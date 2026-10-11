#!/usr/bin/env python3
"""
Synchronize AIKit canonical memory and the Claude compatibility mirror.

Usage:
    python3 scripts/sync-memory-mirror.py --source canonical
    python3 scripts/sync-memory-mirror.py --source claude
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from memory_paths import (
    CANONICAL_MEMORY_PATH,
    CLAUDE_MEMORY_PATH,
    ensure_memory_structure,
    sync_memory_tree,
)
from workspace_paths import get_toolkit_root, resolve_workspace_root


ROOT = get_toolkit_root()
WORKSPACE_ROOT = ROOT
TEMPLATE_INDEX = ROOT / "base" / "memory" / "INDEX.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync AIKit memory paths")
    parser.add_argument(
        "--source",
        choices=("canonical", "claude"),
        default="canonical",
        help="which memory tree is the source of truth for this sync run",
    )
    parser.add_argument("--workspace-root", type=Path, help="Workspace root for canonical and Claude memory trees")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace_root = resolve_workspace_root(args.workspace_root)
    canonical_dir = workspace_root / CANONICAL_MEMORY_PATH
    claude_dir = workspace_root / CLAUDE_MEMORY_PATH

    ensure_memory_structure(canonical_dir, TEMPLATE_INDEX)
    ensure_memory_structure(claude_dir, TEMPLATE_INDEX)

    if args.source == "canonical":
        sync_memory_tree(canonical_dir, claude_dir, TEMPLATE_INDEX)
        print(f"Synchronized {CANONICAL_MEMORY_PATH} -> {CLAUDE_MEMORY_PATH}")
    else:
        sync_memory_tree(claude_dir, canonical_dir, TEMPLATE_INDEX)
        print(f"Synchronized {CLAUDE_MEMORY_PATH} -> {CANONICAL_MEMORY_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
