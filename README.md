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
- Custom workloads (future expansion)

## Inventory

| Host | Group | IP | Description |
|------|-------|-----|-------------|
| `glow-941` | homelab | `10.1.68.99` | Homelab LXC |
| `xenon-935` | homelab | `10.1.71.5` | Homelab LXC |
| `core-263` | homelab | `10.1.68.141` | Homelab VM |
| `mesh-143` | homelab | `10.1.68.112` | Homelab LXC |
| `veil-945` | homelab | `10.1.68.62` | Homelab LXC |
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

## Architecture

```text
.
├── ansible.cfg                          # Ansible configuration
├── inventory/
│   └── hosts.yml                        # Host inventory with groups
├── playbooks/
│   ├── site.yml                         # Main entry point (unattended-upgrades)
│   └── maintenance.yml                  # On-demand maintenance (server-maintenance)
├── roles/
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
│   └── server_maintenance/
│       ├── defaults/main.yml            # Configurable variables
│       ├── meta/main.yml                # Galaxy metadata
│       ├── tasks/
│       │   ├── main.yml                 # Entry point (install/uninstall blocks)
│       │   ├── validate_config.yml      # Pre-flight validation
│       │   └── uninstall.yml            # Symmetric teardown
│       └── README.md                    # Role documentation
├── .ansible-lint                        # Linting rules
├── .pre-commit-config.yaml              # Pre-commit hook configuration
├── .yamllint.yml                        # YAML linting rules
├── justfile                             # Task runner shortcuts
└── .github/
    ├── renovate.json                    # Automated dependency updates
    └── workflows/
        ├── pre-commit.yml               # CI lint checks
        └── autotag.yml                  # Automatic version tagging
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

# Maintenance playbook — package upgrades + disk cleanup
ansible-playbook playbooks/maintenance.yml --check    # Dry run
ansible-playbook playbooks/maintenance.yml            # Deploy
ansible-playbook playbooks/maintenance.yml --limit vps # VPS hosts only

# Run with tag filtering
ansible-playbook playbooks/site.yml --tags install-unattended_upgrades
ansible-playbook playbooks/maintenance.yml --tags install-server_maintenance
```

## Roles

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
