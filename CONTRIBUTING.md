<!--
SPDX-FileCopyrightText: 2026 Ruhani Rabin (Rabin)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contributing to Ansible Proxmox Node-02

Thank you for contributing to this project. This document covers how to propose changes, run validations, and follow the project's conventions.

## Table of Contents

- [Getting Started](#getting-started)
- [Branch Workflow](#branch-workflow)
- [Commit Conventions](#commit-conventions)
- [Running Validations](#running-validations)
- [Adding a New Role](#adding-a-new-role)
- [Role Design Patterns](#role-design-patterns)
- [Pull Requests](#pull-requests)
- [License](#license)

## Getting Started

### Requirements

- Ansible 2.14+
- Python 3.10+
- SSH key-based access to target hosts

### Install pre-commit hooks (recommended)

```bash
pip install pre-commit
pre-commit install --hook-type pre-push
```

This installs hooks that run on `git push` to catch lint errors before they reach the remote.

## Branch Workflow

All changes require a feature or fix branch. Direct commits to `main` are only for trivial typo edits.

| Prefix | Usage |
|--------|-------|
| `feat/` | New roles, features, or capabilities |
| `fix/` | Bug fixes |
| `docs/` | Documentation updates |
| `refactor/` | Structural improvements without behavior change |
| `chore/` | Maintenance, CI, tooling |
| `test/` | Test additions or fixes |

Example: `feat/docker-role`, `fix/unattended-upgrades-reboot`

## Commit Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): short summary

type: feat, fix, docs, refactor, chore, test
scope: the role or component affected
summary: imperative mood, max 72 chars
```

Examples:
```
feat(server-maintenance): add docker prune task
fix(unattended-upgrades): correct reboot time default
docs(readme): add maintenance playbook usage
chore(ci): add renovate config for dependency updates
```

One logical change per commit. Split large refactors into multiple commits.

## Running Validations

### Lint with ansible-lint

```bash
# Quick lint
just lint

# Production-profile lint
just validate

# Fix auto-fixable issues
just format
```

### Run pre-commit manually

```bash
pre-commit run --all-files
```

### Dry-run a playbook

```bash
ansible-playbook playbooks/site.yml --check --diff
ansible-playbook playbooks/maintenance.yml --check --diff
```

### Run with tag filtering

```bash
# Only install tasks (skip uninstall)
ansible-playbook playbooks/site.yml --tags install-unattended_upgrades

# Only unattended-upgrades role
ansible-playbook playbooks/site.yml --tags setup-unattended_upgrades
```

## Adding a New Role

When creating a new role, follow this structure:

```
roles/<role-name>/
├── defaults/main.yml       # Variables with documented defaults
├── meta/main.yml           # Galaxy metadata and dependencies
├── tasks/
│   ├── main.yml            # Entry point (install/uninstall blocks)
│   ├── validate_config.yml # Pre-flight validation
│   └── uninstall.yml       # Symmetric teardown
├── templates/              # Jinja2 templates (if needed)
└── README.md               # Role documentation
```

Every role **must** have:
1. `meta/main.yml` with galaxy metadata
2. `defaults/main.yml` with documented defaults
3. `tasks/validate_config.yml` — fail early on bad config
4. `tasks/uninstall.yml` — symmetric teardown
5. Task tags: `setup-all`, `setup-<role>`, `install-all`, `install-<role>`, `remove-all`, `remove-<role>`

## Role Design Patterns

### Auto/Custom Variable Layering

Use the `_auto` + `_custom` pattern for extensible lists:

```yaml
# defaults/main.yml
my_role_items: []
my_role_items_custom: []
my_role_items_merged: "{{ my_role_items + my_role_items_custom }}"
```

Users can set `_custom` without fear of breaking internal role logic.

### Computed Defaults

Chain variables so users only change one value:

```yaml
my_role_version: "1.2.3"
my_role_image: "registry/image:{{ my_role_version }}"
```

### Pre-flight Validation

`validate_config.yml` runs before any installation. Use `ansible.builtin.fail` with clear messages:

```yaml
- name: Fail if hostname is empty
  ansible.builtin.fail:
    msg: "my_role_hostname is required"
  when: my_role_hostname | length == 0
```

### Idempotent Operations

All tasks must be idempotent. Use `changed_when` and `failed_when` appropriately:

```yaml
- name: Clean apt cache
  ansible.builtin.command: apt-get clean
  changed_when: true  # Always reports as changed (cache is cleared)
```

### Conditional Restarts

Track what changed and restart only when necessary:

```yaml
- name: Determine if restart is needed
  ansible.builtin.set_fact:
    my_role_restart_necessary: >-
      {{
        my_role_config_result.changed | default(false)
        or my_role_service_result.changed | default(false)
      }}
```

## Pull Requests

PRs should include:

1. **What changed** — one-line summary
2. **Why** — problem being solved or feature being added
3. **Risk** — anything that could break existing deployments
4. **Validation** — commands run to verify (lint output, --check results)
5. **Rollback** — how to revert if something breaks

Stacked PRs for large changes:
- `docs/` or ADR first
- Schema/config changes
- Runtime changes
- Ops/CI updates

## License

This project is licensed under GPL-3.0-or-later. Every file must include an SPDX header:

```yaml
# SPDX-FileCopyrightText: 2026 Ruhani Rabin (Rabin)
#
# SPDX-License-Identifier: GPL-3.0-or-later
```

See the [LICENSE](LICENSE) file for the full license text.
