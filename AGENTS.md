<!--
SPDX-FileCopyrightText: 2026 Ruhani Rabin (Rabin)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Agent Guide

This repository manages Debian and Ubuntu homelab hosts with Ansible. It includes Proxmox-hosted LXCs and VMs, remote VPS hosts, a Semaphore UI role, maintenance roles, and a read-only Linux inventory collector that renders private SilverBullet drafts.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before non-trivial work. This file adds agent-specific guardrails for working safely in this repo.

## Success Standard

- Keep changes small, idempotent, and matched to existing role/playbook patterns.
- Read the immediate playbook, role defaults, tasks, templates, docs, and inventory usage before editing.
- Preserve safe operation on real remote hosts. Do not turn an inspection task into a mutation task implicitly.
- Verify with the narrowest meaningful local checks, then state what could not be run from the current machine.
- Surface privacy risks before collected host data can enter Git or the public mirror.

## Repository Shape

```text
inventory/hosts.yml                  Managed Linux host inventory
playbooks/site.yml                   Unattended-upgrades entry point
playbooks/maintenance.yml            On-demand maintenance entry point
playbooks/semaphore.yml              Semaphore UI setup entry point
playbooks/inventory_collect.yml       Read-only Linux inventory collection
roles/                                Ansible roles and role docs
scripts/                              Inventory render/promote helpers
docs/inventory-collector.md           Inventory workflow and privacy notes
.github/workflows/                   CI, autotag, and public mirror sync
```

## High-Risk Boundaries

### Managed hosts

- Assume playbooks target real hosts.
- Prefer `--syntax-check`, `--check`, `--diff`, and limited host selection before live changes when behavior changes.
- Do not add mutating inventory collection tasks. `playbooks/inventory_collect.yml` is read-only by design.
- Keep offline/sleeping host handling tolerant in inventory collection.
- Keep task failures visible unless a non-fatal collector path records the failure intentionally.

### Private inventory data

- `inventory_reports/` is generated private output and is intentionally gitignored.
- Raw inventory can contain real hostnames, IPs, packages, Docker metadata, container labels, mount paths, listening ports, Tailscale data, usernames, and topology.
- Do not commit generated raw JSON or rendered SilverBullet drafts without an explicit user request and an explicit privacy review.
- Do not assume the public mirror anonymizer is sufficient for collected inventory output.

### Public mirror

- Pushes to private `main` run `.github/workflows/sync-public.yml`.
- The public sync runs `.github/workflows/anonymize.py` with `.github/workflows/mapping.json`.
- The anonymizer covers configured IP prefixes and hostname patterns; it is not a general secret scrubber.
- Treat any new committed file as potentially mirrored publicly unless it is excluded by the sync logic.

## Ansible Conventions

- Use existing roles and helpers before introducing a new pattern.
- Keep roles symmetric:
  - documented defaults
  - config validation
  - install/setup path
  - uninstall/remove path, including a clear no-op path for stateless roles
- Follow existing task tags from [CONTRIBUTING.md](CONTRIBUTING.md) when adding roles or major role surfaces.
- Keep tasks idempotent where the operation can be idempotent.
- Set `changed_when` and `failed_when` deliberately for command or shell tasks.
- Use fully qualified Ansible module names.
- Use `ansible.builtin.command` over shell when shell syntax is not needed.
- For shell pipelines, use Bash explicitly and set `pipefail` consistently with existing code.
- Match role variable prefixes and the repo's `_auto`, `_custom`, and merged-variable patterns where relevant.

## Inventory Collector Rules

- Keep Linux collection agentless over the existing Ansible SSH access.
- Collectors may read host, package, service, storage, Docker, network, and Tailscale state.
- Generated reports must stay under `inventory_reports/` by default.
- Rendered drafts are review staging, not automatically authoritative SilverBullet pages.
- Promotion into SilverBullet must remain explicit through the promote script or a user-approved equivalent.
- Use `python3` in Debian-facing task recipes; do not assume a `python` command exists on the control node.
- Preserve the separation between:
  - primary node addresses
  - Tailscale addresses
  - other interface or bridge addresses
- Keep Docker service pages readable: prefer labels, normalize Swarm/Easypanel replica suffixes, qualify generic Compose names, and avoid stopped duplicate service pages when a running equivalent exists.

## Validation

Primary CI is the pre-commit workflow on pushes and pull requests.

- If GitHub `pre-commit` completes successfully, treat that validation as
  passed even when GitHub also reports the known Actions Node.js runtime
  deprecation annotation for `actions/checkout@v4` or
  `actions/setup-python@v5`. Do not block unrelated inventory work on that
  annotation unless the workflow itself fails or the user asks to address CI
  maintenance.

Run locally when available:

```bash
pre-commit run --all-files
just lint
just validate
git diff --check
```

Playbook checks when Ansible is available:

```bash
ansible-playbook playbooks/site.yml --syntax-check
ansible-playbook playbooks/maintenance.yml --syntax-check
ansible-playbook playbooks/semaphore.yml --syntax-check
ansible-playbook playbooks/inventory_collect.yml --syntax-check
```

For behavior changes that can affect hosts, prefer a limited dry run when it is meaningful:

```bash
ansible-playbook playbooks/site.yml --check --diff --limit <host-or-group>
ansible-playbook playbooks/maintenance.yml --check --diff --limit <host-or-group>
```

Inventory renderer checks:

```bash
python3 -m py_compile scripts/render_silverbullet_inventory.py scripts/promote_silverbullet_inventory.py
just inventory-render
```

If a command is unavailable in the current environment, say so. Do not claim a lint or Ansible check passed when it was skipped.

## Git, Commits, And Releases

- Follow the branch workflow and commit format in [CONTRIBUTING.md](CONTRIBUTING.md) unless the user explicitly asks for a direct `main` sync.
- Use Conventional Commits:

```text
type(scope): short imperative summary
```

- Supported types in this repo are `feat`, `fix`, `docs`, `refactor`, `chore`, and `test`.
- Prefer useful scopes such as `inventory`, `semaphore`, `server-maintenance`, `unattended-upgrades`, `docs`, or `ci`.
- `.github/workflows/autotag.yml` tags pushes to `main`:
  - `feat` drives a minor bump.
  - `fix` drives a patch bump.
  - default bump is patch.
  - `BREAKING CHANGE` drives a major bump.
- There is no checked-in `CHANGELOG.md` at this time. Do not claim one was updated. Update relevant docs for behavior changes, and add a changelog only if the user asks to introduce that artifact.

## Lint And License Details

- Pre-commit checks include line endings, Markdown lint, codespell, REUSE, ansible-lint, and Renovate config validation.
- Markdown files should use HTML comment SPDX headers rather than `#` comment SPDX lines, otherwise Markdown lint reads them as headings.
- Add SPDX headers to new files in the format appropriate to the file type.
- Keep REUSE annotations in sync for files that cannot carry inline SPDX metadata.

## Documentation

- Update README or focused docs when user-facing commands or behavior change.
- Keep role README files aligned with role behavior.
- Keep `docs/inventory-collector.md` aligned with collector, renderer, privacy, and promotion behavior.
- Avoid documenting generated private inventory by copying raw host reports into tracked docs.
