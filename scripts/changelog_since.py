#!/usr/bin/env python3
"""
Print released changelog sections newer than the provided version.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from release_utils import version_tuple


ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_FILE = ROOT / "CHANGELOG.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show changelog entries newer than a given version")
    parser.add_argument("--from-version", required=True, help="last installed version")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    current: str | None = None
    sections: list[tuple[str, list[str]]] = []

    for line in CHANGELOG_FILE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\] - (\d{4}-\d{2}-\d{2})$", line)
        if match:
            current = match.group(1)
            sections.append((current, [line]))
            continue
        if current is not None:
            sections[-1][1].append(line)

    try:
        from_version = version_tuple(args.from_version)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    emitted = False
    for version, lines in sections:
        if version_tuple(version) > from_version:
            print("\n".join(lines).rstrip())
            print()
            emitted = True

    if not emitted:
        print("(новых release sections в CHANGELOG нет)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
