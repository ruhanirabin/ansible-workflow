<!--
SPDX-FileCopyrightText: 2026 Ruhani Rabin (Rabin)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Server Maintenance

On-demand system updates and disk cleanup for Debian/Ubuntu hosts.

## What It Does

1. **System Package Updates** — `apt dist-upgrade` with configurable hold list
2. **Apt Cache Clean** — `apt-get clean`
3. **Orphaned Package Removal** — `apt autoremove --purge`
4. **Journal Log Vacuum** — truncates journals to configurable size (default: 100M)
5. **Old Kernel Removal** — keeps currently running kernel + 1 previous
6. **Docker Prune** — removes dangling images, stopped containers, unused volumes (auto-skipped if Docker not installed)

## Usage

### Run on all hosts

```bash
ansible-playbook playbooks/maintenance.yml
```

### Run on specific hosts

```bash
ansible-playbook playbooks/maintenance.yml --limit bolt-602
```

### Dry run (check what would change)

```bash
ansible-playbook playbooks/maintenance.yml --check --diff
```

### Run specific phases via tags

```bash
# Skip Docker cleanup
ansible-playbook playbooks/maintenance.yml --skip-tags server-maintenance

# Only package upgrades (skips cleanup)
ansible-playbook playbooks/maintenance.yml --tags install-server_maintenance
```

## Variables

| Variable | Default | Description |
|---|---|---|
| `server_maintenance_enabled` | `true` | Enable/disable the role entirely |
| `server_maintenance_run_upgrade` | `true` | Run apt dist-upgrade |
| `server_maintenance_hold_packages` | `[]` | Packages to temporarily hold during upgrade |
| `server_maintenance_hold_packages_custom` | `[]` | Additional hold packages (auto/custom layering) |
| `server_maintenance_apt_clean` | `true` | Run apt-get clean |
| `server_maintenance_apt_autoremove` | `true` | Remove orphaned packages |
| `server_maintenance_journal_max_size` | `"100M"` | Max journal log size after vacuum |
| `server_maintenance_remove_old_kernels` | `true` | Remove old kernel packages |
| `server_maintenance_docker_prune` | `true` | Prune Docker resources (auto-skipped if no Docker) |

## Example: Hold NVIDIA drivers on GPU hosts

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

## Example: Disable on a specific host

```yaml
# inventory/hosts.yml
vps:
  hosts:
    luna-683:
      ansible_host: 104.212.224.100
      server_maintenance_enabled: false
```

## Task Tags

| Tag | Description |
|---|---|
| `setup-all` | All setup tasks |
| `setup-server_maintenance` | This role's setup tasks |
| `install-all` | All install tasks |
| `install-server_maintenance` | This role's install tasks |
| `remove-all` | All removal tasks |
| `remove-server_maintenance` | This role's removal tasks |
