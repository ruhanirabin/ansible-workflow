# SPDX-FileCopyrightText: 2026 Ruhani Rabin (Rabin)
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render read-only Ansible inventory snapshots as SilverBullet Markdown."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_REPORT_ROOT = Path.home() / "inventory_reports" / "ansible-proxmox-blade-954"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def parse_json_stdout(value: str, fallback: Any) -> Any:
    if not value.strip():
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def parse_json_lines(value: str) -> list[dict[str, Any]]:
    rows = []
    for line in value.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def slug_to_title(value: str) -> str:
    value = value.strip().strip("/")
    value = re.sub(r"[_-]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.title() if value else "Unnamed Service"


def normalize_container_name(value: str) -> str:
    name = value.strip().strip("/")
    return re.sub(r"\.\d+\.[A-Za-z0-9]{8,}$", "", name)


def compose_project(labels: dict[str, Any]) -> str:
    return str(labels.get("com.docker.compose.project", "")).strip()


def qualify_generic_service_name(service: str, project: str) -> str:
    generic_names = {
        "app",
        "api",
        "backend",
        "cache",
        "client",
        "database",
        "db",
        "frontend",
        "postgres",
        "redis",
        "server",
        "web",
        "worker",
    }
    if project and service.lower() in generic_names:
        return f"{slug_to_title(project)} {slug_to_title(service)}"
    return slug_to_title(service)


def safe_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "-", value).strip().rstrip(".")
    return cleaned or "Unnamed"


def yaml_scalar(value: Any) -> str:
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T.*", text):
        return json.dumps(text)
    if re.fullmatch(r"[A-Za-z0-9_.:/@+-]+", text):
        return text
    return json.dumps(text)


def yaml_list(values: list[str]) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(yaml_scalar(value) for value in values) + "]"


def frontmatter(data: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in data.items():
        if value in ("", None, [], {}):
            continue
        if isinstance(value, list):
            lines.append(f"{key}: {yaml_list(value)}")
        else:
            lines.append(f"{key}: {yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def command_stdout(snapshot: dict[str, Any], key: str) -> str:
    return str(snapshot.get("command_results", {}).get(key, {}).get("stdout", ""))


def docker_available(snapshot: dict[str, Any]) -> bool:
    return int(snapshot.get("command_results", {}).get("docker_cli", {}).get("rc", 999)) == 0


def tailscale_available(snapshot: dict[str, Any]) -> bool:
    return int(snapshot.get("command_results", {}).get("tailscale_cli", {}).get("rc", 999)) == 0


def docker_inspect(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    parsed = parse_json_stdout(command_stdout(snapshot, "docker_inspect"), [])
    return parsed if isinstance(parsed, list) else []


def docker_rows(snapshot: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return parse_json_lines(command_stdout(snapshot, key))


def container_running(container: dict[str, Any]) -> bool:
    return bool(container.get("State", {}).get("Running"))


def parse_inventory_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def inventory_age_days(snapshot: dict[str, Any], now: datetime) -> int | None:
    collected_at = parse_inventory_datetime(snapshot.get("collected_at"))
    if collected_at is None:
        return None
    return max((now - collected_at).days, 0)


def local_inventory_timestamp(value: Any, fallback: datetime) -> str:
    collected_at = parse_inventory_datetime(value)
    if collected_at is None:
        collected_at = fallback
    return collected_at.astimezone().replace(microsecond=0).isoformat()


def is_stale(snapshot: dict[str, Any], now: datetime, stale_days: int) -> bool:
    age_days = inventory_age_days(snapshot, now)
    return age_days is None or age_days > stale_days


def package_count(snapshot: dict[str, Any]) -> int:
    packages = snapshot.get("ansible_facts", {}).get("packages", {})
    return len(packages) if isinstance(packages, dict) else 0


def active_service_count(snapshot: dict[str, Any]) -> int:
    services = snapshot.get("ansible_facts", {}).get("services", {})
    if not isinstance(services, dict):
        return 0
    return sum(1 for service in services.values() if service.get("state") == "running")


def memory_mb(facts: dict[str, Any]) -> int | None:
    value = facts.get("memtotal_mb")
    return int(value) if isinstance(value, int | float) else None


def cpu_count(facts: dict[str, Any]) -> int | None:
    value = facts.get("processor_vcpus") or facts.get("processor_count")
    return int(value) if isinstance(value, int | float) else None


def ipv4_addresses(facts: dict[str, Any]) -> list[str]:
    addresses = []
    default_ipv4 = facts.get("default_ipv4", {})
    if isinstance(default_ipv4, dict) and default_ipv4.get("address"):
        addresses.append(str(default_ipv4["address"]))
    for value in facts.get("all_ipv4_addresses", []) or []:
        value = str(value)
        if value != "127.0.0.1" and value not in addresses:
            addresses.append(value)
    return addresses


def primary_ipv4_address(facts: dict[str, Any]) -> str:
    default_ipv4 = facts.get("default_ipv4", {})
    return str(default_ipv4.get("address", "")) if isinstance(default_ipv4, dict) else ""


def tailscale_ipv4_addresses(snapshot: dict[str, Any]) -> list[str]:
    return [line.strip() for line in command_stdout(snapshot, "tailscale_ipv4").splitlines() if line.strip()]


def other_ipv4_addresses(facts: dict[str, Any], excluded: set[str]) -> list[str]:
    return [address for address in ipv4_addresses(facts) if address not in excluded]


def tailscale_status(snapshot: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_json_stdout(command_stdout(snapshot, "tailscale_status"), {})
    return parsed if isinstance(parsed, dict) else {}


def tailscale_dns_name(snapshot: dict[str, Any]) -> str:
    status = tailscale_status(snapshot)
    self_status = status.get("Self", {})
    if not isinstance(self_status, dict):
        return ""
    return str(self_status.get("DNSName", "")).rstrip(".")


def render_text_block(value: str) -> str:
    if not value.strip():
        return "_None detected._\n"
    return "\n".join(["```text", value.strip(), "```\n"])


def lsblk_devices(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    parsed = parse_json_stdout(command_stdout(snapshot, "lsblk"), {})
    devices = parsed.get("blockdevices", []) if isinstance(parsed, dict) else []
    return devices if isinstance(devices, list) else []


def flatten_block_devices(devices: list[dict[str, Any]], prefix: str = "") -> list[dict[str, Any]]:
    rows = []
    for device in devices:
        current = dict(device)
        current["name"] = f"{prefix}{device.get('name', '')}"
        rows.append(current)
        children = device.get("children") or []
        if isinstance(children, list):
            rows.extend(flatten_block_devices(children, prefix="  "))
    return rows


def mountpoints(device: dict[str, Any]) -> str:
    values = device.get("mountpoints") or []
    return ", ".join(str(value) for value in values if value)


def render_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "_None detected._\n"
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        output.append("| " + " | ".join(format_table_cell(cell) for cell in row) + " |")
    return "\n".join(output) + "\n"


def format_table_cell(value: Any) -> str:
    return str(value).replace("\n", " ").replace("|", r"\|")


def declared_automations(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    values = snapshot.get("declared_automations", [])
    return [value for value in values if isinstance(value, dict)] if isinstance(values, list) else []


def automation_check_results(snapshot: dict[str, Any], key: str) -> list[dict[str, Any]]:
    values = snapshot.get("automation_checks", {}).get(key, [])
    return [value for value in values if isinstance(value, dict)] if isinstance(values, list) else []


def artifact_from_check(result: dict[str, Any]) -> dict[str, Any]:
    item = result.get("item", [])
    if isinstance(item, list) and len(item) > 1 and isinstance(item[1], dict):
        return item[1]
    return {}


def script_artifact_observation(snapshot: dict[str, Any], path: str) -> str:
    for result in automation_check_results(snapshot, "script_stats"):
        artifact = artifact_from_check(result)
        if artifact.get("path") != path:
            continue
        if result.get("skipped"):
            return "not checked"
        stat = result.get("stat", {})
        return "present" if isinstance(stat, dict) and stat.get("exists") else "missing"
    return "not checked"


def parse_systemd_properties(value: str) -> dict[str, str]:
    properties = {}
    for line in value.splitlines():
        key, _, raw_value = line.partition("=")
        if key:
            properties[key] = raw_value
    return properties


def systemd_artifact_observation(snapshot: dict[str, Any], name: str, check_key: str) -> str:
    for result in automation_check_results(snapshot, check_key):
        artifact = artifact_from_check(result)
        if artifact.get("name") != name:
            continue
        if result.get("skipped"):
            return "not checked"
        properties = parse_systemd_properties(str(result.get("stdout", "")))
        load_state = properties.get("LoadState", "")
        if load_state in ("", "not-found"):
            return "missing"
        active_state = properties.get("ActiveState", "unknown")
        unit_file_state = properties.get("UnitFileState", "unknown")
        return f"{load_state}; active={active_state}; enabled={unit_file_state}"
    return "not checked"


def cron_artifact_observation(snapshot: dict[str, Any], user: str, match: str) -> str:
    for result in automation_check_results(snapshot, "cron_artifacts"):
        artifact = artifact_from_check(result)
        if artifact.get("user") != user or artifact.get("match") != match:
            continue
        if result.get("skipped"):
            return "not checked"
        if int(result.get("rc", 999)) != 0:
            return "missing"
        return "present" if match in str(result.get("stdout", "")) else "missing"
    return "not checked"


def automation_artifact_label(artifact: dict[str, Any]) -> str:
    artifact_type = str(artifact.get("type", "unknown"))
    if artifact_type == "script":
        target = artifact.get("path")
    elif artifact_type == "cron":
        target = f"{artifact.get('user', 'missing user')}: {artifact.get('match', 'missing match')}"
    else:
        target = artifact.get("name")
    return f"{artifact_type}: {target or 'missing target'}"


def automation_artifact_observation(snapshot: dict[str, Any], artifact: dict[str, Any]) -> str:
    artifact_type = artifact.get("type")
    if artifact_type == "script":
        return script_artifact_observation(snapshot, str(artifact.get("path", "")))
    if artifact_type in ("systemd_service", "systemd_timer"):
        return systemd_artifact_observation(snapshot, str(artifact.get("name", "")), "systemd_artifacts")
    if artifact_type in ("systemd_user_service", "systemd_user_timer"):
        return systemd_artifact_observation(snapshot, str(artifact.get("name", "")), "systemd_user_artifacts")
    if artifact_type == "cron":
        return cron_artifact_observation(
            snapshot,
            str(artifact.get("user", "")),
            str(artifact.get("match", "")),
        )
    return "unsupported"


def automation_rows(snapshot: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for automation in declared_automations(snapshot):
        artifacts = automation.get("artifacts", [])
        if not isinstance(artifacts, list) or not artifacts:
            rows.append(
                [
                    automation.get("name") or automation.get("id", ""),
                    automation.get("purpose", ""),
                    "_No artifacts declared._",
                    "not checked",
                ]
            )
            continue
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            rows.append(
                [
                    automation.get("name") or automation.get("id", ""),
                    automation.get("purpose", ""),
                    automation_artifact_label(artifact),
                    automation_artifact_observation(snapshot, artifact),
                ]
            )
    return rows


def declared_automation_paths(snapshot: dict[str, Any]) -> set[str]:
    paths = set()
    for automation in declared_automations(snapshot):
        for artifact in automation.get("artifacts", []) or []:
            if isinstance(artifact, dict) and artifact.get("type") == "script" and artifact.get("path"):
                paths.add(str(artifact["path"]))
    return paths


def declared_systemd_unit_names(snapshot: dict[str, Any]) -> set[str]:
    names = set()
    systemd_types = {"systemd_service", "systemd_timer"}
    for automation in declared_automations(snapshot):
        for artifact in automation.get("artifacts", []) or []:
            if isinstance(artifact, dict) and artifact.get("type") in systemd_types and artifact.get("name"):
                names.add(str(artifact["name"]))
    return names


def automation_candidate_rows(snapshot: dict[str, Any]) -> list[list[Any]]:
    rows = []
    declared_paths = declared_automation_paths(snapshot)
    for path in command_stdout(snapshot, "automation_script_candidates").splitlines():
        path = path.strip()
        if path and path not in declared_paths:
            rows.append(["script", path])

    declared_units = declared_systemd_unit_names(snapshot)
    for path in command_stdout(snapshot, "automation_systemd_candidates").splitlines():
        path = path.strip()
        name = Path(path).name
        if path and name not in declared_units:
            rows.append(["systemd unit", path])
    return rows


def snapshot_area(snapshot: dict[str, Any]) -> str:
    groups = snapshot.get("group_names", [])
    return "homelab" if {"homelab", "proxmox_shells"} & set(groups) else "vps"


def render_node(snapshot: dict[str, Any], now: datetime, stale_days: int) -> str:
    facts = snapshot.get("ansible_facts", {})
    hostname = snapshot["inventory_hostname"]
    containers = docker_inspect(snapshot)
    docker_summary = docker_rows(snapshot, "docker_containers")
    age_days = inventory_age_days(snapshot, now)
    stale = is_stale(snapshot, now, stale_days)
    primary_ipv4 = primary_ipv4_address(facts)
    tailscale_ipv4 = tailscale_ipv4_addresses(snapshot)
    remaining_ipv4 = other_ipv4_addresses(facts, {primary_ipv4, *tailscale_ipv4})
    front = frontmatter(
        {
            "tags": ["inventory_node", "inventory"],
            "status": "active",
            "area": snapshot_area(snapshot),
            "role": facts.get("virtualization_role", "unknown"),
            "hostname": facts.get("hostname", hostname),
            "ansible_host": snapshot.get("ansible_host", ""),
            "os_family": facts.get("os_family", ""),
            "distribution": facts.get("distribution", ""),
            "distribution_version": facts.get("distribution_version", ""),
            "kernel": facts.get("kernel", ""),
            "virtualization_type": facts.get("virtualization_type", ""),
            "docker": docker_available(snapshot),
            "tailscale": tailscale_available(snapshot),
            "tailscale_dns": tailscale_dns_name(snapshot),
            "tailscale_ipv4": tailscale_ipv4,
            "package_count": package_count(snapshot),
            "running_service_count": active_service_count(snapshot),
            "last_inventory": local_inventory_timestamp(snapshot.get("collected_at"), now),
            "inventory_age_days": age_days,
            "possibly_stale": stale,
        }
    )

    storage_rows = []
    for device in flatten_block_devices(lsblk_devices(snapshot)):
        storage_rows.append(
            [
                device.get("name", ""),
                device.get("type", ""),
                device.get("size", ""),
                device.get("fstype", ""),
                mountpoints(device),
            ]
        )

    container_rows = []
    for item in docker_summary:
        container_rows.append(
            [
                item.get("Names", ""),
                item.get("Image", ""),
                item.get("State", ""),
                item.get("Status", ""),
                item.get("Ports", ""),
            ]
        )

    ports = command_stdout(snapshot, "listening_ports").splitlines()
    port_rows = [[line] for line in ports[:80]]

    lines = [
        front,
        f"# {hostname}",
        "",
        "> Generated inventory page. Review before copying into the main SilverBullet space.",
        "",
        "## Summary",
        "",
        f"- Inventory host: `{hostname}`",
        f"- System hostname: `{facts.get('fqdn') or facts.get('hostname') or hostname}`",
        f"- OS: `{facts.get('distribution', '')} {facts.get('distribution_version', '')}`",
        f"- Kernel: `{facts.get('kernel', '')}`",
        f"- CPU cores: `{cpu_count(facts) or ''}`",
        f"- Memory: `{memory_mb(facts) or ''} MB`",
        f"- Virtualization: `{facts.get('virtualization_type', '')}` / `{facts.get('virtualization_role', '')}`",
        *optional_summary_line("Primary IPv4", primary_ipv4),
        *optional_summary_line("Tailscale IPv4", ", ".join(tailscale_ipv4)),
        *optional_summary_line("Other IPv4", ", ".join(remaining_ipv4)),
        f"- Packages: `{package_count(snapshot)}`",
        f"- Running system services: `{active_service_count(snapshot)}`",
        f"- Docker containers: `{len(containers)}`",
        f"- Inventory age: `{age_days if age_days is not None else 'unknown'} days`",
        f"- Possibly stale: `{str(stale).lower()}`",
        "",
        "## Storage",
        "",
        render_table(["Name", "Type", "Size", "Filesystem", "Mountpoints"], storage_rows),
        "## Docker Containers",
        "",
        render_table(["Name", "Image", "State", "Status", "Ports"], container_rows),
        "## Listening Ports",
        "",
        render_table(["Socket"], port_rows),
        "## Declared Automations",
        "",
        render_table(["Automation", "Purpose", "Artifact", "Observed"], automation_rows(snapshot)),
        "## Candidate Automation Artifacts",
        "",
        "> Review candidates before declaring them as tracked automations.",
        "",
        render_table(["Type", "Artifact"], automation_candidate_rows(snapshot)),
        "## Tailscale",
        "",
        f"- Installed: `{str(tailscale_available(snapshot)).lower()}`",
        *optional_summary_line("DNS", tailscale_dns_name(snapshot)),
        *optional_summary_line("IPv4", ", ".join(tailscale_ipv4)),
        "",
        "### Serve Status",
        "",
        render_text_block(command_stdout(snapshot, "tailscale_serve_text")),
        "### Funnel Status",
        "",
        render_text_block(command_stdout(snapshot, "tailscale_funnel_text")),
        "## Related",
        "",
        "${query[[from index.tag \"inventory_service\" where node = \"" + hostname + "\"]]}",
        "",
    ]
    return "\n".join(lines)


def service_name_from_container(container: dict[str, Any]) -> str:
    labels = container.get("Config", {}).get("Labels") or {}
    if labels.get("com.docker.compose.service"):
        return qualify_generic_service_name(str(labels["com.docker.compose.service"]), compose_project(labels))
    if labels.get("com.docker.swarm.service.name"):
        return slug_to_title(labels["com.docker.swarm.service.name"])
    return slug_to_title(normalize_container_name(str(container.get("Name", ""))))


def format_host_binding(binding: dict[str, Any]) -> str:
    host_ip = str(binding.get("HostIp", ""))
    host_port = str(binding.get("HostPort", ""))
    if host_ip == "::":
        host_ip = "[::]"
    return f"{host_ip}:{host_port}" if host_ip else host_port


def container_mount_rows(container: dict[str, Any]) -> list[list[Any]]:
    rows = []
    mounts = container.get("Mounts") or []
    if not isinstance(mounts, list):
        return rows
    for mount in mounts:
        if not isinstance(mount, dict):
            continue
        rows.append(
            [
                mount.get("Type", ""),
                mount.get("Source", ""),
                mount.get("Destination", ""),
                mount.get("Mode", ""),
                str(bool(mount.get("RW"))).lower(),
            ]
        )
    return rows


def optional_summary_line(label: str, value: str) -> list[str]:
    return [f"- {label}: `{value}`"] if value else []


def render_service(
    service_name: str,
    node: str,
    area: str,
    container: dict[str, Any],
    snapshot: dict[str, Any],
    now: datetime,
    stale_days: int,
) -> str:
    state = container.get("State", {})
    config = container.get("Config", {})
    labels = config.get("Labels") or {}
    image = config.get("Image", "")
    project = compose_project(labels)
    age_days = inventory_age_days(snapshot, now)
    stale = is_stale(snapshot, now, stale_days)
    front = frontmatter(
        {
            "tags": ["inventory_service", "inventory"],
            "status": "active" if container_running(container) else "inactive",
            "area": area,
            "node": node,
            "source": "docker",
            "container": str(container.get("Name", "")).strip("/"),
            "image": image,
            "compose_project": project,
            "mount_count": len(container_mount_rows(container)),
            "last_inventory": local_inventory_timestamp(snapshot.get("collected_at"), now),
            "inventory_age_days": age_days,
            "possibly_stale": stale,
        }
    )
    ports = container.get("NetworkSettings", {}).get("Ports") or {}
    port_rows = []
    for container_port, bindings in sorted(ports.items()):
        if not bindings:
            port_rows.append([container_port, ""])
            continue
        for binding in bindings:
            port_rows.append([container_port, format_host_binding(binding)])
    mount_rows = container_mount_rows(container)

    return "\n".join(
        [
            front,
            f"# {service_name}",
            "",
            "> Generated candidate service page from Docker inventory. Review before promoting.",
            "",
            "## Summary",
            "",
            f"- Node: `[[Inventory/Nodes/{node}]]`",
            f"- Container: `{str(container.get('Name', '')).strip('/')}`",
            *optional_summary_line("Compose project", project),
            f"- Image: `{image}`",
            f"- Running: `{str(container_running(container)).lower()}`",
            f"- Inventory age: `{age_days if age_days is not None else 'unknown'} days`",
            f"- Possibly stale: `{str(stale).lower()}`",
            "",
            "## Ports",
            "",
            render_table(["Container", "Host"], port_rows),
            "## Mounts",
            "",
            render_table(["Type", "Host Source", "Container Path", "Mode", "Writable"], mount_rows),
            "## Related",
            "",
            f"- [[Inventory/Nodes/{node}]]",
            "",
        ]
    )


def inventory_node_rows(snapshots: list[dict[str, Any]], now: datetime, stale_days: int) -> list[list[Any]]:
    rows = []
    for snapshot in sorted(snapshots, key=lambda item: item["inventory_hostname"]):
        facts = snapshot.get("ansible_facts", {})
        hostname = snapshot["inventory_hostname"]
        rows.append(
            [
                f"[[Inventory/Nodes/{hostname}]]",
                snapshot_area(snapshot),
                facts.get("distribution", ""),
                facts.get("distribution_version", ""),
                "yes" if docker_available(snapshot) else "no",
                snapshot.get("collected_at", ""),
                "yes" if is_stale(snapshot, now, stale_days) else "no",
            ]
        )
    return rows


def render_inventory_folder_page(
    snapshots: list[dict[str, Any]],
    rendered_service_count: int,
    now: datetime,
    stale_days: int,
) -> str:
    docker_hosts = sum(1 for snapshot in snapshots if docker_available(snapshot))
    stale_nodes = sum(1 for snapshot in snapshots if is_stale(snapshot, now, stale_days))
    rows = inventory_node_rows(snapshots, now, stale_days)

    front = frontmatter(
        {
            "tags": ["dashboard", "inventory"],
            "status": "generated",
            "generated_at": local_inventory_timestamp(None, now),
            "node_count": len(snapshots),
            "docker_host_count": docker_hosts,
            "service_count": rendered_service_count,
            "stale_node_count": stale_nodes,
            "stale_after_days": stale_days,
        }
    )
    return "\n".join(
        [
            front,
            "# Inventory",
            "",
            "> Generated inventory summary. Review before copying into the main SilverBullet space.",
            "",
            "## Summary",
            "",
            f"- Nodes rendered: `{len(snapshots)}`",
            f"- Docker hosts: `{docker_hosts}`",
            f"- Docker service pages rendered: `{rendered_service_count}`",
            f"- Stale nodes: `{stale_nodes}`",
            f"- Stale threshold: `{stale_days} days`",
            "",
            "## Nodes",
            "",
            "- Folder page: [[Inventory/Nodes]]",
            "",
            render_table(["Node", "Area", "Distribution", "Version", "Docker", "Last Inventory", "Stale"], rows),
            "## Services",
            "",
            "- Folder page: [[Inventory/Services]]",
            f"- Generated Docker service pages rendered: `{rendered_service_count}`",
            "",
        ]
    )


def render_inventory_nodes_folder_page(snapshots: list[dict[str, Any]], now: datetime, stale_days: int) -> str:
    stale_nodes = sum(1 for snapshot in snapshots if is_stale(snapshot, now, stale_days))
    front = frontmatter(
        {
            "tags": ["dashboard", "inventory"],
            "status": "generated",
            "generated_at": local_inventory_timestamp(None, now),
            "node_count": len(snapshots),
            "stale_node_count": stale_nodes,
            "stale_after_days": stale_days,
        }
    )
    return "\n".join(
        [
            front,
            "# Inventory Nodes",
            "",
            "> Generated inventory summary. Review before copying into the main SilverBullet space.",
            "",
            "Node drafts rendered from reachable Linux inventory hosts.",
            "",
            render_table(
                ["Node", "Area", "Distribution", "Version", "Docker", "Last Inventory", "Stale"],
                inventory_node_rows(snapshots, now, stale_days),
            ),
            "## Related",
            "",
            "- [[Inventory]]",
            "",
        ]
    )


def render_inventory_services_folder_page(
    service_rows: list[list[Any]],
    now: datetime,
    stale_days: int,
) -> str:
    front = frontmatter(
        {
            "tags": ["dashboard", "inventory"],
            "status": "generated",
            "generated_at": local_inventory_timestamp(None, now),
            "service_count": len(service_rows),
            "stale_after_days": stale_days,
        }
    )
    return "\n".join(
        [
            front,
            "# Inventory Services",
            "",
            "> Generated inventory summary. Review before copying into the main SilverBullet space.",
            "",
            "Docker-derived service candidates stay separate from curated [[Services]] pages until reviewed.",
            "",
            render_table(["Service", "Node", "Area", "Image", "Running", "Last Inventory", "Stale"], service_rows),
            "## Related",
            "",
            "- [[Inventory]]",
            "",
        ]
    )


def render(input_dir: Path, output_dir: Path, clean: bool, stale_days: int) -> None:
    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    inventory_dir = output_dir / "Inventory"
    nodes_dir = inventory_dir / "Nodes"
    services_dir = inventory_dir / "Services"
    nodes_dir.mkdir(parents=True, exist_ok=True)
    services_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    snapshots = [load_json(path) for path in sorted(input_dir.glob("*.json"))]
    service_entries: list[tuple[str, str, str, dict[str, Any], dict[str, Any]]] = []
    for snapshot in snapshots:
        node_name = snapshot["inventory_hostname"]
        area = snapshot_area(snapshot)
        (nodes_dir / f"{safe_filename(node_name)}.md").write_text(
            render_node(snapshot, now, stale_days),
            encoding="utf-8",
        )
        for container in docker_inspect(snapshot):
            service_name = service_name_from_container(container)
            service_entries.append((service_name, node_name, area, container, snapshot))

    active_service_keys = {
        (node_name, service_name)
        for service_name, node_name, _area, container, _snapshot in service_entries
        if container_running(container)
    }

    service_names: dict[str, int] = {}
    rendered_service_count = 0
    rendered_service_rows = []
    for service_name, node_name, area, container, snapshot in service_entries:
        if not container_running(container) and (node_name, service_name) in active_service_keys:
            continue

        count = service_names.get(service_name, 0) + 1
        service_names[service_name] = count
        filename = service_name if count == 1 else f"{service_name} - {node_name}"
        safe_service_filename = safe_filename(filename)
        (services_dir / f"{safe_service_filename}.md").write_text(
            render_service(service_name, node_name, area, container, snapshot, now, stale_days),
            encoding="utf-8",
        )
        rendered_service_rows.append(
            [
                f"[[Inventory/Services/{safe_service_filename}]]",
                f"[[Inventory/Nodes/{node_name}]]",
                area,
                container.get("Config", {}).get("Image", ""),
                "yes" if container_running(container) else "no",
                snapshot.get("collected_at", ""),
                "yes" if is_stale(snapshot, now, stale_days) else "no",
            ]
        )
        rendered_service_count += 1

    (output_dir / "Inventory.md").write_text(
        render_inventory_folder_page(snapshots, rendered_service_count, now, stale_days),
        encoding="utf-8",
    )
    (inventory_dir / "Nodes.md").write_text(
        render_inventory_nodes_folder_page(snapshots, now, stale_days),
        encoding="utf-8",
    )
    (inventory_dir / "Services.md").write_text(
        render_inventory_services_folder_page(rendered_service_rows, now, stale_days),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_REPORT_ROOT / "raw", type=Path)
    parser.add_argument("--output", default=DEFAULT_REPORT_ROOT / "silverbullet", type=Path)
    parser.add_argument("--no-clean", action="store_true", help="Keep existing rendered files")
    parser.add_argument("--stale-days", default=7, type=int, help="Mark rendered pages stale after this many days")
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input directory does not exist: {args.input}")
    render(args.input, args.output, clean=not args.no_clean, stale_days=args.stale_days)


if __name__ == "__main__":
    main()
