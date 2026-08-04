# SPDX-FileCopyrightText: 2026 Ruhani Rabin (Rabin)
#
# SPDX-License-Identifier: GPL-3.0-or-later
# Ansible Proxmox Node-02 — Task Runner
# Install: https://github.com/casey/just

default:
    @just --list --justfile '{{justfile()}}'

lint:
    ansible-lint .

validate:
    ansible-lint --profile production .

format:
    just lint --fix

inventory-collect:
    ansible-playbook playbooks/inventory_collect.yml

inventory-render:
    python3 scripts/render_silverbullet_inventory.py

inventory-promote target:
    python3 scripts/promote_silverbullet_inventory.py --target '{{target}}'

inventory-promote-dry-run target:
    python3 scripts/promote_silverbullet_inventory.py --target '{{target}}' --dry-run

inventory:
    just inventory-collect
