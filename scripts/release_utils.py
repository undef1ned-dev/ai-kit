#!/usr/bin/env python3
"""
Helpers for AIKit release and version discipline.
"""

from __future__ import annotations

import re
from pathlib import Path


SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def read_version(version_file: Path) -> str:
    return version_file.read_text(encoding="utf-8").strip()


def is_semver(value: str) -> bool:
    return bool(SEMVER_RE.fullmatch(value.strip()))


def version_tuple(value: str) -> tuple[int, int, int]:
    if not is_semver(value):
        raise ValueError(f"Invalid semver version: {value}")
    major, minor, patch = value.strip().split(".")
    return int(major), int(minor), int(patch)


def parse_changelog_versions(changelog_text: str) -> list[str]:
    versions: list[str] = []
    for line in changelog_text.splitlines():
        match = re.match(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\] - \d{4}-\d{2}-\d{2}$", line.strip())
        if match:
            versions.append(match.group(1))
    return versions


def parse_unreleased_body(changelog_text: str) -> str:
    marker = "## [Unreleased]"
    if marker not in changelog_text:
        return ""
    _, _, remainder = changelog_text.partition(marker)
    body, _, _ = remainder.partition("\n## [")
    return body.strip()


def unreleased_has_entries(changelog_text: str) -> bool:
    body = parse_unreleased_body(changelog_text)
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("###"):
            continue
        if stripped == "- Пока пусто.":
            continue
        return True
    return False
