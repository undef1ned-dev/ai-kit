#!/usr/bin/env python3
"""
Helpers for AIKit canonical memory layout.

Canonical memory lives in `.aikit/memory/`.
Claude-compatible projects and the active Claude adapter additionally mirror
that state into `.claude/memory/`.
"""

from __future__ import annotations

import shutil
from pathlib import Path


CANONICAL_MEMORY_PATH = Path(".aikit/memory")
CLAUDE_MEMORY_PATH = Path(".claude/memory")
MEMORY_SUBDIRS = (
    "decisions",
    "patterns",
    "corrections",
    "tasks",
    "tasks/archive",
    "features",
)
GITKEEP_PATHS = (
    "decisions/.gitkeep",
    "patterns/.gitkeep",
    "corrections/.gitkeep",
    "tasks/.gitkeep",
    "tasks/archive/.gitkeep",
    "features/.gitkeep",
)


def ensure_memory_structure(memory_dir: Path, template_index: Path) -> None:
    memory_dir.mkdir(parents=True, exist_ok=True)
    for subdir in MEMORY_SUBDIRS:
        (memory_dir / subdir).mkdir(parents=True, exist_ok=True)
    for rel_path in GITKEEP_PATHS:
        (memory_dir / rel_path).touch(exist_ok=True)
    index_path = memory_dir / "INDEX.md"
    if not index_path.exists() and template_index.exists():
        shutil.copy2(template_index, index_path)


def clear_memory_contents(memory_dir: Path) -> None:
    if not memory_dir.exists():
        return
    for item in memory_dir.iterdir():
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        except FileNotFoundError:
            # Parallel sync or cleanup may already remove the same entry.
            continue


def sync_memory_tree(source_dir: Path, destination_dir: Path, template_index: Path) -> None:
    ensure_memory_structure(source_dir, template_index)
    clear_memory_contents(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    for item in sorted(source_dir.iterdir()):
        target = destination_dir / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    ensure_memory_structure(destination_dir, template_index)


def find_memory_source(root: Path, template_fallback: bool = True) -> Path | None:
    candidates = [
        root / CANONICAL_MEMORY_PATH,
        root / CLAUDE_MEMORY_PATH,
    ]
    if template_fallback:
        candidates.append(root / "base" / "memory")
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None
