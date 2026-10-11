#!/usr/bin/env python3
"""Helpers for separating toolkit root and workspace root paths."""

from __future__ import annotations

import os
from pathlib import Path


TOOLKIT_ROOT = Path(__file__).resolve().parent.parent


def get_toolkit_root() -> Path:
    return TOOLKIT_ROOT


def resolve_workspace_root(explicit_workspace_root: Path | str | None = None) -> Path:
    if explicit_workspace_root is not None:
        return Path(explicit_workspace_root).expanduser().resolve()

    env_value = os.environ.get("AIKIT_WORKSPACE_ROOT", "").strip()
    if env_value:
        return Path(env_value).expanduser().resolve()

    cwd = Path.cwd().resolve()
    if cwd == TOOLKIT_ROOT and TOOLKIT_ROOT.name == ".aikit-config":
        return TOOLKIT_ROOT.parent.resolve()
    return cwd


def runtime_root(workspace_root: Path) -> Path:
    return workspace_root / ".aikit" / "runtime"


def memory_root(workspace_root: Path) -> Path:
    return workspace_root / ".aikit" / "memory"


def resolve_from_root(path: Path | str, root: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (root / candidate).resolve()


def display_path(path: Path, *, workspace_root: Path | None = None, toolkit_root: Path | None = None) -> str:
    resolved = path.resolve()
    for root in (workspace_root, toolkit_root):
        if root is None:
            continue
        root_resolved = root.resolve()
        if resolved.is_relative_to(root_resolved):
            return str(resolved.relative_to(root_resolved))
    return str(resolved)
