#!/usr/bin/env python3
"""
Bump the AIKit version from Conventional Commits, without a model.

The release workflow (.github/workflows/version.yml) runs it after every merge into main:

    breaking change (`type!:` or a `BREAKING CHANGE:` footer)  → major
    feat                                                       → minor
    anything else (fix, perf, refactor, docs, chore, …)        → patch

Only commits that touch what ships in the plugins count (PLUGIN_PATHS: base/, profiles/, packs/, hooks/,
deck/, scripts/ …). A merge of docs, evals or CI alone leaves the version as it is: users would get
an update notice for nothing. Merge commits and earlier release commits are skipped — their content is
counted through the commits they bring in.

The range starts at the last commit that changed VERSION, so a run that failed is caught up by the next one.

Usage:
    python3 scripts/bump-version.py                 # print the level and the next version, change nothing
    python3 scripts/bump-version.py --write         # also write VERSION and a CHANGELOG.md section
    python3 scripts/bump-version.py --base <ref>    # count commits after <ref> instead

With --write the version, level and changelog section go to $GITHUB_OUTPUT when it is set.
Standard library only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys
from pathlib import Path

from release_utils import is_semver, read_version, version_tuple

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"
# What the plugins ship: the core plugin root is the repository, so this is the part users run.
# Keep in sync with `paths:` of .github/workflows/version.yml (checked by scripts/ci/test-bump-version.py)
PLUGIN_PATHS = (
    "base/",
    "profiles/",
    "packs/",
    "presets/",
    "templates/",
    "adapters/",
    "hooks/",
    "deck/",
    "scripts/",
    ".claude-plugin/",
    ".codex-plugin/",
    ".antigravity-plugin/",
)
# Inside PLUGIN_PATHS, but used only to develop the kit
NON_PLUGIN_PATHS = ("scripts/ci/", "deck/tests/")
LEVELS = ("patch", "minor", "major")
RELEASE_SUBJECT = re.compile(r"^chore\(release\): v?\d+\.\d+\.\d+")
SKIPPED_SUBJECT = re.compile(r"^(?:Merge |chore\(release\): )")
HEADER = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^()]*)\))?(?P<breaking>!)?: (?P<description>.+)$")
BREAKING_FOOTER = re.compile(r"(?m)^BREAKING[ -]CHANGE: ")
# Keep a Changelog headings; breaking changes open the Changed list
CHANGELOG_GROUPS = (("feat", "Added"), ("major", "Changed"), ("other", "Changed"), ("fix", "Fixed"))
UNRELEASED_MARKER = "## [Unreleased]"
FIELD_SEPARATOR = "\x1f"
RECORD_SEPARATOR = "\x1e"


def touches_plugins(files: list[str]) -> bool:
    return any(
        path.startswith(PLUGIN_PATHS) and not path.startswith(NON_PLUGIN_PATHS) for path in files
    )


def commit_level(message: str) -> str:
    """Level of one commit message; messages outside Conventional Commits count as patch."""
    subject = message.strip().splitlines()[0] if message.strip() else ""
    match = HEADER.match(subject)
    if match and match.group("breaking") or BREAKING_FOOTER.search(message):
        return "major"
    if match and match.group("type") == "feat":
        return "minor"
    return "patch"


def bump_level(messages: list[str]) -> str | None:
    """The highest level among the messages; None when there is nothing to release."""
    levels = [commit_level(message) for message in messages if not SKIPPED_SUBJECT.match(message.strip())]
    return max(levels, key=LEVELS.index) if levels else None


def next_version(version: str, level: str) -> str:
    major, minor, patch = version_tuple(version)
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def changelog_entry(message: str) -> tuple[str, str]:
    """(group, line) of a commit for the changelog section."""
    subject = message.strip().splitlines()[0]
    match = HEADER.match(subject)
    if not match:
        return "other", f"- {subject}"
    scope = f"{match.group('scope')}: " if match.group("scope") else ""
    text = f"{scope}{match.group('description')}"
    if commit_level(message) == "major":
        return "major", f"- **Несовместимо.** {text}"
    if match.group("type") in {"feat", "fix"}:
        return match.group("type"), f"- {text}"
    return "other", f"- {text}"


def changelog_section(version: str, date: str, messages: list[str]) -> str:
    entries = [changelog_entry(message) for message in messages if not SKIPPED_SUBJECT.match(message.strip())]
    lines = [f"## [{version}] - {date}"]
    headings: dict[str, list[str]] = {}
    for group, heading in CHANGELOG_GROUPS:
        items = [line for entry_group, line in entries if entry_group == group]
        if items:
            headings.setdefault(heading, []).extend(items)
    for heading, items in headings.items():
        lines += ["", f"### {heading}", *items]
    return "\n".join(lines) + "\n"


def insert_section(changelog: str, section: str) -> str:
    """The new section goes right after [Unreleased] (or after the title when there is none)."""
    if UNRELEASED_MARKER in changelog:
        head, _, rest = changelog.partition(UNRELEASED_MARKER)
        body, separator, tail = rest.partition("\n## [")
        unreleased = UNRELEASED_MARKER + body.rstrip("\n") + "\n\n"
        return head + unreleased + section + ("\n## [" + tail if separator else "")
    match = re.search(r"(?m)^## \[", changelog)
    if not match:
        return changelog.rstrip("\n") + "\n\n" + section
    return changelog[: match.start()] + section + "\n" + changelog[match.start():]


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, check=True, encoding="utf-8", errors="replace"
    )
    return result.stdout


def default_base() -> str:
    """The last commit that changed VERSION: the previous release."""
    return git("log", "-1", "--format=%H", "--", "VERSION").strip()


def plugin_commits(base: str) -> list[str]:
    """Messages of the non-merge commits after base that touch the plugins, oldest first."""
    revision_range = f"{base}..HEAD" if base else "HEAD"
    log = git("log", "--reverse", "--no-merges", f"--format=%H{FIELD_SEPARATOR}%B{RECORD_SEPARATOR}", revision_range)
    messages = []
    for record in log.split(RECORD_SEPARATOR):
        if FIELD_SEPARATOR not in record:
            continue
        sha, message = record.strip("\n").split(FIELD_SEPARATOR, 1)
        files = git("diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha).splitlines()
        if touches_plugins(files) and not RELEASE_SUBJECT.match(message.strip()):
            messages.append(message.strip())
    return messages


def github_output(values: dict[str, str]) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8", newline="\n") as output:
        for key, value in values.items():
            if "\n" in value:
                output.write(f"{key}<<AIKIT_EOF\n{value.rstrip()}\nAIKIT_EOF\n")
            else:
                output.write(f"{key}={value}\n")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Bump the AIKit version from Conventional Commits")
    parser.add_argument("--base", help="count commits after this ref (default: the last commit that changed VERSION)")
    parser.add_argument("--write", action="store_true", help="write VERSION and a CHANGELOG.md section")
    args = parser.parse_args()

    current = read_version(VERSION_FILE)
    if not is_semver(current):
        print(f"В VERSION не semver X.Y.Z: «{current}»", file=sys.stderr)
        return 2
    messages = plugin_commits(args.base if args.base is not None else default_base())
    level = bump_level(messages)
    if level is None:
        print(f"Версия {current} не меняется: после прошлого релиза нет коммитов, которые попадают в плагины")
        github_output({"version": "", "level": ""})
        return 0
    version = next_version(current, level)
    section = changelog_section(version, datetime.date.today().isoformat(), messages)
    print(f"{current} → {version} ({level}, коммитов: {len(messages)})")
    print(section)
    if args.write:
        VERSION_FILE.write_bytes(f"{version}\n".encode("utf-8"))
        changelog = CHANGELOG_FILE.read_text(encoding="utf-8") if CHANGELOG_FILE.exists() else "# Changelog\n"
        CHANGELOG_FILE.write_bytes(insert_section(changelog, section).encode("utf-8"))
        github_output({"version": version, "level": level, "notes": section})
    return 0


if __name__ == "__main__":
    sys.exit(main())
