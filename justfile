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
