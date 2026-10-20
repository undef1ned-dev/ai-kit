#!/usr/bin/env python3
"""
Team settings of a project connected to AIKit: .aikit/settings.json, kept in git.

    {"commit": "ask"}   — the git-commit skill offers 2-3 messages and waits for the user's choice (default)
    {"commit": "auto"}  — the skill picks the message by the same rules and commits without asking

Installers write the choice made during setup; the AIKit Deck toggles it. Keys this script does not know stay.

Usage:
    python3 scripts/project_settings.py --workspace . --commit auto
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SETTINGS_FILE = Path(".aikit") / "settings.json"
COMMIT_MODES = ("ask", "auto")
DEFAULT_COMMIT_MODE = "ask"


def read(workspace: Path) -> dict:
    path = workspace / SETTINGS_FILE
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def commit_mode(workspace: Path) -> str:
    mode = read(workspace).get("commit")
    return mode if mode in COMMIT_MODES else DEFAULT_COMMIT_MODE


def write(workspace: Path, commit: str | None) -> str:
    """Keep the current mode when none is given; a new project gets the default."""
    settings = read(workspace)
    settings["commit"] = commit if commit in COMMIT_MODES else commit_mode(workspace)
    path = workspace / SETTINGS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(settings, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return settings["commit"]


def describe(mode: str) -> str:
    return "спрашивать сообщение" if mode == "ask" else "автоматически по правилам"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Write AIKit team settings of a project")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--commit", choices=COMMIT_MODES)
    args = parser.parse_args()
    mode = write(Path(args.workspace).resolve(), args.commit)
    print(f"Коммиты: {describe(mode)} ({SETTINGS_FILE.as_posix()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
