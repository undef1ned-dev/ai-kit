#!/usr/bin/env python3
"""
Helpers for the AIKit team memory layout.

Team memory lives in `.aikit/memory/` of the project and is shared through git:
decisions, patterns, agent corrections and per-module memory.
"""

from __future__ import annotations

import shutil
from pathlib import Path


CANONICAL_MEMORY_PATH = Path(".aikit/memory")
MEMORY_SUBDIRS = (
    "decisions",
    "patterns",
    "corrections",
    "features",
)


def ensure_memory_structure(memory_dir: Path, template_index: Path) -> None:
    memory_dir.mkdir(parents=True, exist_ok=True)
    for subdir in MEMORY_SUBDIRS:
        (memory_dir / subdir).mkdir(parents=True, exist_ok=True)
        (memory_dir / subdir / ".gitkeep").touch(exist_ok=True)
    index_path = memory_dir / "INDEX.md"
    if not index_path.exists() and template_index.exists():
        shutil.copy2(template_index, index_path)


def find_memory_source(root: Path, template_fallback: bool = True) -> Path | None:
    candidates = [root / CANONICAL_MEMORY_PATH]
    if template_fallback:
        candidates.append(root / "base" / "memory")
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None
