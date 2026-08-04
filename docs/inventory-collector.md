<!--
SPDX-FileCopyrightText: 2026 Ruhani Rabin (Rabin)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Read-Only Inventory Collector

This repository can collect host inventory through the existing Ansible SSH access without installing an agent on managed hosts.

The playbook targets the `inventory_linux` inventory group. This is separate
from the `maintenance_linux` and `unattended_upgrades_linux` groups used by
update workflows, so collector-only hosts can be inventoried without being
included in scheduled update runs.

## Privacy Model

Generated inventory reports are private artifacts. They may contain hostnames, IP addresses, package names, Docker image names, bind mounts, exposed ports, usernames, and service names.

The playbook writes generated reports under the control user's home directory by
default. If a run overrides the report root back into this repository, the
generated `inventory_reports/` directory is intentionally ignored by Git and
must not be committed. The public repository sync only receives the collector
code and documentation, not collected inventory data.

## Collect

```bash
just inventory-collect
```

This writes one raw JSON snapshot per host to:

```text
~/inventory_reports/ansible-proxmox-blade-954/raw/
```

The report root defaults to
`$HOME/inventory_reports/ansible-proxmox-blade-954` for the control user running
Ansible. Set `inventory_report_root` to override it for a run. The playbook is
read-only. It gathers Ansible facts, package facts, service facts, block
devices, listening ports, Docker metadata when Docker is available, and
Tailscale metadata when the Tailscale CLI is available.

Offline or sleeping hosts are skipped after an explicit reachability check. They will not block reports for reachable hosts, and their previous report file remains untouched until the host is collected again. Per-host fact collection errors are recorded in the raw JSON under `collection_errors` instead of failing the whole inventory run.
Raw snapshots for hosts removed from the `inventory_linux` inventory scope are
deleted from the local report root before each collection run, so removed
machines do not continue to render from old JSON files.

### Declared Automations

Track custom scripts, services, and timers with host inventory metadata instead
of relying only on broad host discovery:

```yaml
inventory_automations:
  - id: restic-home-backup
    name: Restic home backup
    purpose: Back up selected app data.
    artifacts:
      - type: script
        path: /usr/local/sbin/restic-home-backup.sh
      - type: systemd_service
        name: restic-home-backup.service
      - type: systemd_timer
        name: restic-home-backup.timer
      - type: systemd_user_service
        user: root
        uid: 0
        name: root-session-helper.service
      - type: cron
        user: app
        match: /usr/local/sbin/restic-home-backup.sh
```

The collector records the declarations and checks declared `script`,
`systemd_service`, `systemd_timer`, `systemd_user_service`, and
`systemd_user_timer`, and `cron` artifacts read-only. Systemd user artifacts
require the declared account `user` and numeric `uid` so the collector can read
the correct user session bus. Cron artifacts read the declared user's crontab
and report whether its `match` string is present; rendered drafts do not print
the full crontab. Rendered node drafts show the declared artifact and the
observed state.

The collector also lists review candidates from files directly under
`/usr/local/bin`, `/usr/local/sbin`, and systemd service or timer unit files
directly under `/etc/systemd/system`. Declared script paths and systemd unit
names are removed from those candidate rows. Candidate rows are hints for
catalog review; they are not automatically tracked automations.

## Render SilverBullet Drafts

`playbooks/inventory_collect.yml` renders SilverBullet drafts after collection
by default. Set `inventory_render_silverbullet: false` to keep a collector run
raw-only. To render an existing report root manually:

```bash
python3 scripts/render_silverbullet_inventory.py \
  --input ~/inventory_reports/ansible-proxmox-blade-954/raw \
  --output ~/inventory_reports/ansible-proxmox-blade-954/silverbullet
```

This renders reviewable Markdown drafts to:

```text
~/inventory_reports/ansible-proxmox-blade-954/silverbullet/
├── Inventory.md
└── Inventory/
    ├── Nodes.md
    ├── Nodes/
    ├── Services.md
    └── Services/
```

The generated pages are staging output. Review them before copying any page into
the SilverBullet knowledge space. The `Inventory/` subtree keeps generated
inventory companions separate from hand-maintained `Nodes/` and `Services/`
pages. Generated node and service pages use inventory-specific tags so root
SilverBullet dashboards can stay curated. Docker service pages include port and
mount tables from Docker inspect data so bind mounts and named volume paths
remain visible during review. Node pages separate primary, Tailscale, and other
IPv4 addresses and include Tailscale Serve or Funnel status text when the
Tailscale CLI reports it.

The render step also writes generated SilverBullet folder pages: `Inventory.md`,
`Inventory/Nodes.md`, and `Inventory/Services.md`. `Inventory.md` summarizes
node counts, Docker host counts, service counts, and stale inventory counts.
Generated frontmatter timestamps use the renderer control node's local timezone
and are quoted for SilverBullet; raw report timestamps remain UTC inventory
evidence.
Pages are marked `possibly_stale: true` when their raw snapshot is older than
the stale threshold. The default threshold is seven days.

```bash
python3 scripts/render_silverbullet_inventory.py --stale-days 14
```

## Promote Reviewed Drafts

After reviewing the rendered output, copy it into a SilverBullet space explicitly:

```bash
just inventory-promote-dry-run /path/to/silverbullet-space
just inventory-promote /path/to/silverbullet-space
```

Promotion copies only generated `Inventory.md` and the generated `Inventory/`
subtree. It does not write directly into the hand-maintained SilverBullet
`Nodes/` or `Services/` folders. Existing target files are refreshed only when
they already carry the generated inventory marker; promotion refuses a filename
collision with a hand-maintained SilverBullet page. Promotion also removes
generated pages under the promoted `Inventory/` subtree when they no longer
exist in the freshly rendered source, and removes older generated `Index.md`
folder pages under `Inventory/` when they still carry a generated inventory
marker.

## Full Local Run

```bash
just inventory
```

This runs the collector playbook, which renders after collection by default.

## Scope

The first version collects what each host can report over SSH. Proxmox API data, such as authoritative VMID, LXC or VM config, assigned cores, assigned RAM, and node placement, should be added later as a separate collection path.
