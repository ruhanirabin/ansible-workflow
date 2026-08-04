<!--
SPDX-FileCopyrightText: 2026 Ruhani Rabin (Rabin)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# common_packages

Installs baseline packages needed across managed Debian/Ubuntu nodes.

## Defaults

```yaml
common_packages_enabled: true
common_packages_auto:
  - curl
  - git
  - rsync
  - unzip
  - wget
common_packages_custom: []
common_packages_merged: "{{ common_packages_auto + common_packages_custom }}"
common_packages_update_cache: true
```

## Add extra packages

Add group- or host-specific packages without editing the role:

```yaml
common_packages_custom:
  - jq
  - htop
```

## Run

```bash
ansible-playbook -i inventory playbooks/common_packages.yml --check
ansible-playbook -i inventory playbooks/common_packages.yml
ansible-playbook -i inventory playbooks/common_packages.yml --limit mesh-143
```
