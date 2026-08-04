<!--
SPDX-FileCopyrightText: 2026 Ruhani Rabin (Rabin)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# ssh_authorized_keys

Installs SSH public keys into target users' `authorized_keys` files idempotently.

The role uses Ansible core modules (`getent`, `file`, and `lineinfile`) so it does not require external collections. It matches on the SSH key type + key body, so running it repeatedly will not duplicate keys even if comments differ.

## Defaults

```yaml
ssh_authorized_keys_enabled: true
ssh_authorized_keys_user: root
ssh_authorized_keys_auto:
  - name: proxmox-config-collector
    user: root
    key: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGp6vCP0U1ynai3U92t59+KBhOyS9OiABEkiMrI2IJDO proxmox-config-collector"
ssh_authorized_keys_custom: []
ssh_authorized_keys_merged: "{{ ssh_authorized_keys_auto + ssh_authorized_keys_custom }}"
ssh_authorized_keys_manage_dir: true
```

## Add extra keys

Add group- or host-specific keys without editing the role:

```yaml
ssh_authorized_keys_custom:
  - name: backup-runner
    user: root
    key: "ssh-ed25519 AAAA... backup-runner"
```

## Run

The included playbook targets all homelab nodes except the Debian NUC source host:

```bash
ansible-playbook -i inventory playbooks/ssh_authorized_keys.yml --check
ansible-playbook -i inventory playbooks/ssh_authorized_keys.yml
```

Limit to one host when testing:

```bash
ansible-playbook -i inventory playbooks/ssh_authorized_keys.yml --limit mesh-143
```
