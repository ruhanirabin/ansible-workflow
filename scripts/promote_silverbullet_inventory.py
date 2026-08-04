# SPDX-FileCopyrightText: 2026 Ruhani Rabin (Rabin)
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Copy rendered inventory drafts into a SilverBullet space."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


DEFAULT_REPORT_ROOT = Path.home() / "inventory_reports" / "ansible-proxmox-blade-954"
GENERATED_PATHS = ("Inventory.md", "Inventory")
LEGACY_GENERATED_PATHS = (
    "Inventory/Index.md",
    "Inventory/Nodes/Index.md",
    "Inventory/Services/Index.md",
)
GENERATED_MARKERS = (
    "> Generated inventory page.",
    "> Generated candidate service page from Docker inventory.",
    "> Generated inventory summary.",
)


def generated_inventory_page(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return any(marker in content for marker in GENERATED_MARKERS)


def find_conflicts(source: Path, target: Path) -> list[Path]:
    if not source.exists():
        return []
    if source.is_dir():
        conflicts = []
        for file_path in sorted(path for path in source.rglob("*") if path.is_file()):
            rel_path = file_path.relative_to(source)
            conflicts.extend(find_conflicts(file_path, target / rel_path))
        return conflicts
    if target.exists() and not generated_inventory_page(target):
        return [target]
    return []


def copy_path(source: Path, target: Path, dry_run: bool) -> None:
    if not source.exists():
        return
    if source.is_dir():
        for file_path in sorted(path for path in source.rglob("*") if path.is_file()):
            rel_path = file_path.relative_to(source)
            copy_path(file_path, target / rel_path, dry_run)
        return
    if dry_run:
        print(f"would copy {source} -> {target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    print(f"copied {source} -> {target}")


def prune_empty_dirs(root: Path, source_dirs: set[Path], dry_run: bool) -> None:
    if not root.exists() or not root.is_dir():
        return
    for dir_path in sorted((path for path in root.rglob("*") if path.is_dir()), reverse=True):
        if dir_path.relative_to(root) in source_dirs:
            continue
        try:
            is_empty = not any(dir_path.iterdir())
        except OSError:
            continue
        if not is_empty:
            continue
        if dry_run:
            print(f"would remove empty generated directory {dir_path}")
            continue
        dir_path.rmdir()
        print(f"removed empty generated directory {dir_path}")


def remove_stale_generated_path(source: Path, target: Path, dry_run: bool) -> None:
    if not target.exists():
        return
    if source.exists() and source.is_dir():
        if not target.is_dir():
            return
        source_files = {path.relative_to(source) for path in source.rglob("*") if path.is_file()}
        source_dirs = {path.relative_to(source) for path in source.rglob("*") if path.is_dir()}
        for file_path in sorted(path for path in target.rglob("*") if path.is_file()):
            rel_path = file_path.relative_to(target)
            if rel_path in source_files or not generated_inventory_page(file_path):
                continue
            if dry_run:
                print(f"would remove stale generated page {file_path}")
                continue
            file_path.unlink()
            print(f"removed stale generated page {file_path}")
        prune_empty_dirs(target, source_dirs, dry_run)
        return
    if source.exists():
        return
    if not target.is_file() or not generated_inventory_page(target):
        return
    if dry_run:
        print(f"would remove stale generated page {target}")
        return
    target.unlink()
    print(f"removed stale generated page {target}")


def remove_legacy_generated_path(target: Path, dry_run: bool) -> None:
    if not generated_inventory_page(target):
        return
    if dry_run:
        print(f"would remove legacy generated page {target}")
        return
    target.unlink()
    print(f"removed legacy generated page {target}")


def promote(source: Path, target: Path, dry_run: bool) -> None:
    if not source.exists():
        raise SystemExit(f"Rendered inventory directory does not exist: {source}")
    if not target.exists():
        raise SystemExit(f"SilverBullet target directory does not exist: {target}")
    conflicts = []
    for rel_path in GENERATED_PATHS:
        conflicts.extend(find_conflicts(source / rel_path, target / rel_path))
    if conflicts:
        paths = "\n".join(f"- {path}" for path in conflicts)
        raise SystemExit(f"Promotion refused hand-maintained SilverBullet page collisions:\n{paths}")
    for rel_path in GENERATED_PATHS:
        copy_path(source / rel_path, target / rel_path, dry_run)
    for rel_path in GENERATED_PATHS:
        remove_stale_generated_path(source / rel_path, target / rel_path, dry_run)
    for rel_path in LEGACY_GENERATED_PATHS:
        remove_legacy_generated_path(target / rel_path, dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_REPORT_ROOT / "silverbullet", type=Path)
    parser.add_argument("--target", required=True, type=Path, help="SilverBullet space root")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    promote(args.source, args.target, args.dry_run)


if __name__ == "__main__":
    main()
