<!--
SPDX-FileCopyrightText: 2026 Ruhani Rabin (Rabin)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Unattended Upgrades

Configures automatic security updates via the `unattended-upgrades` package on Debian/Ubuntu hosts.

## What It Does

1. Installs `unattended-upgrades` and `apt-listchanges`
2. Configures update origins (default: security updates only)
3. Sets up automatic reboot with configurable time
4. Enables unused package and kernel cleanup
5. Validates configuration with dry-run after setup
6. Backs up existing config before overwriting

## Usage

### Run on all hosts

```bash
ansible-playbook playbooks/site.yml
```

### Dry run

```bash
ansible-playbook playbooks/site.yml --check --diff
```

## Variables

| Variable | Default | Description |
|---|---|---|
| `unattended_upgrades_enabled` | `true` | Enable/disable the role entirely |
| `unattended_upgrades_packages` | `[unattended-upgrades, apt-listchanges]` | Packages to install |
| `unattended_upgrades_origins` | `[]` | Additional update origins (beyond security defaults) |
| `unattended_upgrades_origins_custom` | `[]` | Additional origins (auto/custom layering) |
| `unattended_upgrades_blacklist` | `[]` | Packages to skip during automatic upgrades |
| `unattended_upgrades_blacklist_custom` | `[]` | Additional blacklist entries (auto/custom layering) |
| `unattended_upgrades_auto_reboot` | `true` | Enable automatic reboot after updates |
| `unattended_upgrades_reboot_time` | `"00:30"` | Reboot time in HH:MM format |
| `unattended_upgrades_remove_unused_deps` | `true` | Remove unused dependencies |
| `unattended_upgrades_remove_new_unused_deps` | `true` | Remove newly unused dependencies |
| `unattended_upgrades_remove_unused_kernel` | `true` | Remove unused kernel packages |
| `unattended_upgrades_mail` | `""` | Email address for reports (empty = no mail) |
| `unattended_upgrades_mail_only_on_error` | `true` | Only send mail on errors |
| `unattended_upgrades_dry_run_enabled` | `true` | Run dry-run validation after config |

## Example: Custom reboot time

```yaml
# inventory/hosts.yml
homelab:
  hosts:
    crest-217:
      ansible_host: 10.1.68.80
      unattended_upgrades_reboot_time: "10:00"
```

## Example: Blacklist packages

```yaml
# inventory/hosts.yml
homelab:
  hosts:
    crest-217:
      ansible_host: 10.1.68.80
      unattended_upgrades_blacklist:
        - "nvidia-driver-535"
        - "nvidia-dkms-535"
        - "libnvidia-*"
```

## Example: Disable on a specific host

```yaml
# inventory/hosts.yml
vps:
  hosts:
    core-483:
      ansible_host: 104.212.224.100
      unattended_upgrades_enabled: false
```

## Disabling the Role

Setting `unattended_upgrades_enabled: false` triggers the uninstall tasks:
- Stops and disables the `unattended-upgrades` service
- Removes configuration files from `/etc/apt/apt.conf.d/`
- Removes the packages (with autoremove and purge)

## Task Tags

| Tag | Description |
|---|---|
| `setup-all` | All setup tasks |
| `setup-unattended_upgrades` | This role's setup tasks |
| `install-all` | All install tasks |
| `install-unattended_upgrades` | This role's install tasks |
| `remove-all` | All removal tasks |
| `remove-unattended_upgrades` | This role's removal tasks |
