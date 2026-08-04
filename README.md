<!--
SPDX-FileCopyrightText: 2026 Ruhani Rabin (Rabin)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Ansible with Proxmox and VPS Hosts

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![ansible-lint](https://img.shields.io/badge/ansible--lint-production-blue?logo=ansible)](https://ansible.readthedocs.io/projects/lint/)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits)](https://conventionalcommits.org)

Automated configuration management for homelab Proxmox LXCs and remote VPS hosts. In this specific case - ansible runs on a separate tiny Proxmox LXC container. Takes as low memory as 128MB and 1 core. This can be replicated on any other host.

## Overview

This repository contains Ansible playbooks and roles to centrally manage:
- **Automatic security updates** (`unattended_upgrades`) — continuous, silent, nightly
- **On-demand maintenance** (`server_maintenance`) — package upgrades and disk cleanup
- **Common packages** (`common_packages`) — baseline tools like `curl`, `git`, `rsync`, `unzip`, and `wget`
- **SSH authorized keys** (`ssh_authorized_keys`) — shared SSH public key deployment without duplicates
- **Semaphore UI setup** (`semaphore`) — web UI for manual and scheduled playbook runs
- **Read-only inventory drafts** (`inventory_collect`) — private Linux inventory snapshots and SilverBullet staging pages
- Custom workloads (future expansion)

## Inventory

Inventory groups separate host context from action eligibility. A host may belong
to multiple groups.

| Group | Purpose |
|-------|---------|
| `inventory_linux` | Linux hosts eligible for read-only inventory collection |
| `unattended_upgrades_linux` | Hosts eligible for unattended-upgrades setup |
| `maintenance_linux` | Hosts eligible for scheduled maintenance tasks |
| `homelab`, `vps`, `proxmox_shells` | Host context groups used by the purpose groups |

Proxmox shell hosts are currently collector-only. They are in
`inventory_linux` through `proxmox_shells`, but they are not in the update
groups used by scheduled playbooks.

| Host | Group | IP | Description |
|------|-------|-----|-------------|
| `glow-941` | homelab | `10.1.68.99` | Homelab LXC |
| `xenon-935` | homelab | `10.1.71.5` | Homelab LXC |
| `core-263` | homelab | `10.1.68.141` | Homelab VM |
| `mesh-143` | homelab | `10.1.68.112` | Homelab LXC |
| `veil-945` | homelab | `10.1.68.62` | Homelab LXC |
| `flux-708` | homelab | `10.1.71.4` | Homelab LXC |
| `wave-956` | homelab | `10.1.71.3` | Homelab LXC |
| `quartz-299` | homelab | `10.1.68.93` | Homelab LXC |
| `veil-693` | homelab | `10.1.71.6` | Homelab LXC |
| `glow-870` | homelab | `10.1.71.31` | Homelab LXC |
| `flux-430` | homelab | `10.1.71.8` | Homelab LXC |
| `veil-117` | homelab | `10.1.71.32` | Homelab LXC |
| `atlas-715` | homelab | `10.1.71.9` | Homelab LXC |
| `crest-217` | homelab | `10.1.68.80` | Homelab VM (custom reboot `10:00`) |
| `bolt-602` | vps | `104.212.224.179` | Remote VPS |
| `spark-493` | vps | `104.212.224.46` | Remote VPS |
| `sage-606` | vps | `104.250.122.142` | Remote VPS |
| `proxmox-node01` | proxmox_shells | `10.1.71.1` | Proxmox shell on Lenovo P520, collector-only |
| `proxmox-node02` | proxmox_shells | `10.1.71.2` | Proxmox shell on Dell OptiPlex 7070 Micro, collector-only |

## Architecture

```text
.
├── ansible.cfg                          # Ansible configuration
├── inventory/
│   └── hosts.yml                        # Host inventory with groups
├── playbooks/
│   ├── common_packages.yml              # Baseline package installation
│   ├── ssh_authorized_keys.yml          # Shared SSH public key installation
│   ├── site.yml                         # Main entry point (unattended-upgrades)
│   ├── maintenance.yml                  # On-demand maintenance (server-maintenance)
│   ├── semaphore.yml                    # Semaphore UI installation/configuration
│   └── inventory_collect.yml            # Read-only Linux inventory collection
├── roles/
│   ├── common_packages/
│   │   ├── defaults/main.yml            # Baseline + custom package lists
│   │   ├── meta/main.yml                # Galaxy metadata
│   │   ├── tasks/
│   │   │   ├── main.yml                 # Install common packages
│   │   │   └── validate_config.yml      # Pre-flight validation
│   │   └── README.md                    # Role documentation
│   ├── ssh_authorized_keys/
│   │   ├── defaults/main.yml            # Shared + custom SSH key lists
│   │   ├── meta/main.yml                # Galaxy metadata
│   │   ├── tasks/
│   │   │   ├── main.yml                 # Install authorized_keys entries
│   │   │   └── validate_config.yml      # Pre-flight validation
│   │   └── README.md                    # Role documentation
│   ├── unattended_upgrades/
│   │   ├── defaults/main.yml            # Configurable variables
│   │   ├── meta/main.yml                # Galaxy metadata
│   │   ├── tasks/
│   │   │   ├── main.yml                 # Entry point (install/uninstall blocks)
│   │   │   ├── validate_config.yml      # Pre-flight validation
│   │   │   └── uninstall.yml            # Symmetric teardown
│   │   └── templates/                   # Jinja2 config templates
│   │       ├── 10periodic.j2
│   │       ├── 20auto-upgrades.j2
│   │       └── 50unattended-upgrades.j2
│   ├── server_maintenance/
│   │   ├── defaults/main.yml            # Configurable variables
│   │   ├── meta/main.yml                # Galaxy metadata
│   │   ├── tasks/
│   │   │   ├── main.yml                 # Entry point (install/uninstall blocks)
│   │   │   ├── validate_config.yml      # Pre-flight validation
│   │   │   └── uninstall.yml            # Symmetric teardown
│   │   └── README.md                    # Role documentation
│   └── semaphore/                        # Semaphore UI role
├── scripts/
│   ├── render_silverbullet_inventory.py # Render private SilverBullet drafts
│   └── promote_silverbullet_inventory.py # Copy reviewed generated inventory drafts
├── docs/
│   └── inventory-collector.md           # Collector/render/promote workflow
├── .ansible-lint                        # Linting rules
├── .pre-commit-config.yaml              # Pre-commit hook configuration
├── .yamllint.yml                        # YAML linting rules
├── justfile                             # Task runner shortcuts
└── .github/
    ├── renovate.json                    # Automated dependency updates
    └── workflows/
        ├── pre-commit.yml               # CI lint checks
        ├── autotag.yml                  # Automatic version tagging
        └── sync-public.yml              # Public mirror anonymization and sync
```

## Quick Start

### Requirements

- Ansible 2.14+ on the control node
- Python 3.10+
- SSH key-based access to all target hosts
- Target hosts: Ubuntu 22.04+ or Debian 12+

### Install pre-commit hooks (recommended)

```bash
pip install pre-commit
pre-commit install --hook-type pre-push
```

### Run

```bash
cd ansible-proxmox-blade-954

# Site playbook — unattended-upgrades configuration
ansible-playbook playbooks/site.yml --check           # Dry run
ansible-playbook playbooks/site.yml                   # Deploy

# Common packages — baseline tools like curl/git/rsync/unzip/wget
ansible-playbook playbooks/common_packages.yml --check # Dry run
ansible-playbook playbooks/common_packages.yml         # Deploy
ansible-playbook playbooks/common_packages.yml --limit mesh-143 # Single host

# SSH authorized keys — install Debian NUC collector key on homelab nodes except debian-nuc
ansible-playbook playbooks/ssh_authorized_keys.yml --check # Dry run
ansible-playbook playbooks/ssh_authorized_keys.yml         # Deploy
ansible-playbook playbooks/ssh_authorized_keys.yml --limit mesh-143 # Single host

# Maintenance playbook — package upgrades + disk cleanup
ansible-playbook playbooks/maintenance.yml --check    # Dry run
ansible-playbook playbooks/maintenance.yml            # Deploy
ansible-playbook playbooks/maintenance.yml --limit vps # VPS hosts only

# Run with tag filtering
ansible-playbook playbooks/site.yml --tags install-unattended_upgrades
ansible-playbook playbooks/maintenance.yml --tags install-server_maintenance
```

## Read-Only Inventory Reports

This repo can collect host inventory through the existing Ansible SSH access and render private SilverBullet draft pages without installing agents on managed hosts.

```bash
just inventory
```

Generated reports are written to
`~/inventory_reports/ansible-proxmox-blade-954/` for the control user running
Ansible because the output may contain private hostnames, IPs, Docker metadata,
package names, mount paths, and exposed ports. Repo-local `inventory_reports/`
output remains ignored by Git when `inventory_report_root` is overridden. See
[docs/inventory-collector.md](docs/inventory-collector.md) for the full
workflow.

Offline or sleeping hosts are ignored during collection so reachable hosts can still produce reports. Collector-only hosts can be added under `inventory_linux` without placing them in the scheduled `maintenance_linux` or `unattended_upgrades_linux` playbook scopes.

Custom scripts, systemd services, systemd timers, systemd user units, and cron
matches can be declared per host with `inventory_automations`. The collector
checks declared artifacts read-only and renders the observed state on the
generated node draft. See [docs/inventory-collector.md](docs/inventory-collector.md)
for the catalog shape.

After review, rendered drafts can be promoted explicitly into the generated
SilverBullet `Inventory.md` folder page and `Inventory/` subtree:

```bash
just inventory-promote-dry-run /path/to/silverbullet-space
just inventory-promote /path/to/silverbullet-space
```

Promotion refreshes generated inventory pages and removes previously promoted
generated pages that are no longer present in the fresh render.

## Workflow And Data Pointers

Use these files as the starting points for day-to-day work:

| Need | Source |
| --- | --- |
| Add or group a managed host | `inventory/hosts.yml` |
| Configure unattended upgrades | `playbooks/site.yml`, `roles/unattended_upgrades/` |
| Run package maintenance | `playbooks/maintenance.yml`, `roles/server_maintenance/` |
| Install common packages | `playbooks/common_packages.yml`, `roles/common_packages/` |
| Install shared SSH public keys | `playbooks/ssh_authorized_keys.yml`, `roles/ssh_authorized_keys/` |
| Install or upgrade Semaphore UI | `playbooks/semaphore.yml`, `roles/semaphore/` |
| Collect Linux inventory | `playbooks/inventory_collect.yml`, `docs/inventory-collector.md` |
| Render or promote inventory drafts | `scripts/render_silverbullet_inventory.py`, `scripts/promote_silverbullet_inventory.py` |
| Review private generated inventory | `~/inventory_reports/ansible-proxmox-blade-954/raw/`, `~/inventory_reports/ansible-proxmox-blade-954/silverbullet/` |

Purpose groups in `inventory/hosts.yml` are the execution boundary:

- `unattended_upgrades_linux` is the scope for `playbooks/site.yml`.
- `maintenance_linux` is the scope for `playbooks/maintenance.yml`.
- `inventory_linux` is the read-only collection scope for `playbooks/inventory_collect.yml`.
- Context groups such as `homelab`, `vps`, and `proxmox_shells` can still be used with `--limit` when they intersect the playbook scope.

Keep generated inventory under `inventory_reports/` private. Collector code and
documentation can be committed; raw host reports and rendered staging pages
should stay out of Git unless a separate privacy review explicitly changes that
boundary.

## Roles

### `common_packages`

Installs baseline tools across targeted Debian/Ubuntu nodes. See [roles/common_packages/README.md](roles/common_packages/README.md) for full documentation.

Default packages:

- `curl`
- `git`
- `rsync`
- `unzip`
- `wget`

Add group- or host-specific packages with `common_packages_custom`.

### `ssh_authorized_keys`

Installs shared SSH public keys into target users' `authorized_keys` files without duplicating existing keys. See [roles/ssh_authorized_keys/README.md](roles/ssh_authorized_keys/README.md) for full documentation.

The included playbook targets `homelab:!debian-nuc`, so the Debian NUC source host is excluded while the collector public key is installed on the other homelab nodes.

### `unattended_upgrades`

Configures automatic security updates with the following defaults:

| Setting | Value |
|---------|-------|
| Update check interval | Daily |
| Security updates only | Yes |
| Unused package cleanup | Yes |
| Unused kernel removal | Yes |
| Automatic reboot | Yes |
| Reboot time | `00:30` (default, overridable per host) |
| Dry-run validation | After config write |
| Config backup | Yes (timestamped `.bak`) |

#### Per-Host Reboot Time Override

You can customize the automatic reboot time for individual hosts by setting `unattended_upgrades_reboot_time` in the inventory:

```yaml
# inventory/hosts.yml
homelab:
  hosts:
    crest-217:
      ansible_host: 10.1.68.80
      unattended_upgrades_reboot_time: "10:00"
```

Hosts without this variable will use the default `00:30`.

#### Per-Host Package Blacklist

You can prevent specific packages from being upgraded by unattended-upgrades on a per-host basis using `unattended_upgrades_blacklist`:

```yaml
# inventory/hosts.yml
homelab:
  hosts:
    crest-217:
      ansible_host: 10.1.68.80
      unattended_upgrades_reboot_time: "10:00"
      unattended_upgrades_blacklist:
        - "nvidia-driver-535"
        - "nvidia-dkms-535"
        - "libnvidia-*"
```

This is useful when certain packages (e.g., NVIDIA drivers) must remain at a specific version and should not be automatically updated.

#### Disabling unattended-upgrades on Specific Hosts

Set `unattended_upgrades_enabled: false` in the inventory to skip this role for a host:

```yaml
homelab:
  hosts:
    ember-793:
      ansible_host: 10.1.71.100
      unattended_upgrades_enabled: false
```

### `server_maintenance`

On-demand system package upgrades and disk cleanup. See [roles/server_maintenance/README.md](roles/server_maintenance/README.md) for full documentation.

**What it does:**

| Phase | Task | Default |
|-------|------|---------|
| Upgrade | `apt dist-upgrade` | enabled |
| Cleanup | `apt-get clean` | enabled |
| Cleanup | `apt autoremove --purge` | enabled |
| Cleanup | Journal log vacuum (100M cap) | always |
| Cleanup | Old kernel removal (keep running + 1) | enabled |
| Cleanup | Docker prune (dangling images, volumes) | auto-skipped if Docker not installed |

**Holding packages during upgrade:**

```yaml
# inventory/hosts.yml
homelab:
  hosts:
    crest-217:
      ansible_host: 10.1.68.80
      server_maintenance_hold_packages:
        - "nvidia-driver-535"
        - "nvidia-dkms-535"
```

#### Disabling server-maintenance on Specific Hosts

Set `server_maintenance_enabled: false` in the inventory to skip this role:

```yaml
vps:
  hosts:
    luna-683:
      ansible_host: 104.212.224.100
      server_maintenance_enabled: false
```

## Reboot Window Rationale

Reboot is scheduled for `00:30` to accommodate hosts that shut down after 1:30 AM. This ensures security updates requiring a reboot are applied before the host sleeps.

## Scheduling Playbooks In Semaphore UI

Semaphore schedules are configured in the UI against Task Templates; they are
not declared in this repository. In Semaphore, each Ansible template selects a
Repository, playbook path, Inventory, optional variables or vaults, and any
`--limit`, tag, or verbosity options needed for the run. See the Semaphore
[Ansible task template](https://semaphoreui.com/docs/user-guide/task-templates/apps/ansible),
[repository](https://semaphoreui.com/docs/user-guide/repositories), and
[inventory](https://semaphoreui.com/docs/user-guide/inventory) documentation.

### Add This Repository

1. In the Semaphore project, create or select the Key Store SSH credential that can read this private Git repository.
2. Create a Repository for `ansible-proxmox-blade-954`.
3. Use the repository URL and branch `main`.
4. Select the repository access key and save it.

### Add The Ansible Inventory

1. Create or select the host SSH credential that Ansible should use for managed hosts.
2. Create an Inventory entry.
3. Choose a file inventory and set the path to `inventory/hosts.yml` so Semaphore uses the repository inventory groups.
4. Attach the user credential and sudo credential if the Semaphore inventory setup requires one for the target hosts.

The inventory path is intentionally repository-relative. Keep group membership
in `inventory/hosts.yml` authoritative instead of maintaining a second static
host list in Semaphore.

### Create Task Templates

Create separate Ansible Playbook Task Templates rather than one broad template:

| Template | Playbook path | Default scope | Schedule guidance |
| --- | --- | --- | --- |
| Unattended upgrades | `playbooks/site.yml` | `unattended_upgrades_linux` | Schedule only after the reboot window and host scope are understood. |
| Server maintenance | `playbooks/maintenance.yml` | `maintenance_linux` | Keep separate from unattended-upgrades; use a maintenance window. |
| Read-only inventory collect | `playbooks/inventory_collect.yml` | `inventory_linux` | Safe to schedule separately; writes raw JSON and SilverBullet draft pages under the control user's report root. |

The playbooks already target purpose groups. Use Semaphore `--limit` only to
narrow a run further, for example to `vps` or one host. Do not widen maintenance
scope by replacing purpose groups with a broader host list.

### Schedule And Verify

1. Test each template manually once from Semaphore and inspect the task log.
2. Add a cron schedule in that template only after the manual run matches the expected host scope.
3. Keep inventory collection on its own schedule if used. It renders private SilverBullet drafts but does not promote them automatically.
4. Review the default report root at `~/inventory_reports/ansible-proxmox-blade-954/` for the Semaphore user running Ansible. Override `inventory_report_root` only when that staging path should move.
5. Keep promotion into SilverBullet explicit after reviewing the generated draft pages.

## Cron (Control Node)

```cron
# Automatic security updates (nightly)
0 0 * * * cd ~/ansible && git pull origin main >/dev/null 2>&1 && ansible-playbook playbooks/site.yml >> logs/run-$(date +\%F).log 2>&1

# On-demand maintenance: weekly Sunday 10:00
0 10 * * 0 cd ~/ansible && git pull origin main >/dev/null 2>&1 && ansible-playbook playbooks/maintenance.yml >> logs/maintenance-$(date +\%F).log 2>&1
```

Runs at midnight: pulls latest playbook, then applies it. Uses `&&` so the playbook only runs if `git pull` succeeds.

The maintenance cron runs weekly (Sunday 10:00 am) to perform dist-upgrades and disk cleanup. Adjust the schedule to your preference.

> **Note:** Create the `logs/` directory before the first run. It is excluded from Git via `.gitignore`.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Branch workflow and commit conventions
- Running validations (lint, pre-commit, --check)
- Adding new roles with proper structure
- Role design patterns (auto/custom layering, validation, etc.)

## Future Additions

- Custom package installations per host group
- Docker container management
- Application-specific deployment roles
- Proxmox host kernel and package update orchestration

## License

[GPL-3.0-or-later](LICENSE)
