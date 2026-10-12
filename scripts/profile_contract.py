#!/usr/bin/env python3
"""
Collect the contracts of the installed profiles into one project file: .aikit/profiles.json.

Source of truth: profiles/<profile>/profile.manifest.json. Agents, skills and hooks of every
runtime read the project file, so they do not need to know the kit layout.

Each profile gets "root": the project folder it lives in, found by the profile's root_markers
("frontend" for a Nuxt app in frontend/, "." for a single-stack repository). Commands run there
and path_signals are relative to it.

The team may edit "commands" and "root" in .aikit/profiles.json (another package manager, extra flags,
a removed command, a different folder). Kit values from the previous run are kept in
.aikit/profiles.kit-defaults.json: a value still equal to the old kit value follows the kit,
a changed or removed one stays as the team left it. Every other field is owned by the kit and refreshed on each run.

Usage:
    python3 scripts/profile_contract.py --profiles a+b [--workspace .]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILES_FILE = Path(".aikit") / "profiles.json"
DEFAULTS_FILE = Path(".aikit") / "profiles.kit-defaults.json"
ABOUT = (
    "Контракты профилей AIKit: агенты по ролям, специалисты, команды, папка профиля. "
    "root — папка профиля в проекте: команды запускаются в ней, path_signals считаются от неё. "
    "commands и root можно менять под проект — обновление кита их не затрёт; остальные поля обновляются из кита. "
    "{files} в команде — изменённые файлы относительно root."
)
SKIPPED_DIRS = {"node_modules", "venv", "__pycache__", "dist", "build", "coverage"}
ROOT_SEARCH_DEPTH = 2


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_contract(profile: str) -> dict:
    path = ROOT / "profiles" / profile / "profile.manifest.json"
    if not path.exists():
        raise SystemExit(f"Нет контракта профиля: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def merge_commands(kit: dict[str, str], previous_kit: dict[str, str] | None, current: dict[str, str] | None) -> dict[str, str]:
    """Kit commands with the team's edits on top. previous_kit is None when the kit never wrote this profile."""
    if current is None:
        return dict(kit)
    if previous_kit is None:
        # The file exists but the kit has no record of its defaults: treat every present value as the team's
        return {
            **{name: current.get(name, command) for name, command in kit.items()},
            **{name: command for name, command in current.items() if name not in kit},
        }
    merged: dict[str, str] = {}
    for name in [*kit, *(name for name in current if name not in kit)]:
        if name in current:
            follows_kit = name in previous_kit and current[name] == previous_kit[name]
            if not follows_kit:
                merged[name] = current[name]
            elif name in kit:
                merged[name] = kit[name]
        elif name not in previous_kit and name in kit:
            merged[name] = kit[name]
    return merged


def candidate_roots(workspace: Path) -> list[str]:
    """Project folders a profile may live in: the workspace itself, then subfolders up to ROOT_SEARCH_DEPTH."""
    roots = ["."]
    level = [workspace]
    for _ in range(ROOT_SEARCH_DEPTH):
        level = sorted(
            child
            for folder in level
            for child in folder.iterdir()
            if child.is_dir() and not child.name.startswith(".") and child.name not in SKIPPED_DIRS
        )
        roots += [child.relative_to(workspace).as_posix() for child in level]
    return roots


def detect_root(workspace: Path, markers: list[str]) -> str:
    """The first folder that holds one of the profile's root markers; "." when none does."""
    for root in candidate_roots(workspace):
        if any((workspace / root / marker).is_file() for marker in markers):
            return root
    return "."


def merge_root(kit: str, previous_kit: str | None, current: str | None) -> str:
    """Detected root unless the team set its own. previous_kit is None when the kit has no record of it."""
    if not current or (previous_kit is not None and current == previous_kit):
        return kit
    return current


def previous_kit_values(record: object) -> tuple[dict[str, str] | None, str | None]:
    """Commands and root from a kit-defaults record; early records held only the commands."""
    if not isinstance(record, dict):
        return None, None
    if "commands" in record:
        return record.get("commands"), record.get("root")
    return record, None


def install(workspace: Path, profiles: list[str]) -> list[str]:
    """Write .aikit/profiles.json for the given profiles. Returns "profile (root)" for each profile written."""
    profiles_path = workspace / PROFILES_FILE
    defaults_path = workspace / DEFAULTS_FILE
    existing = read_json(profiles_path)
    if existing is None:
        print(f"! {PROFILES_FILE} не разобран как JSON — файл не обновлён, исправь его и повтори установку", file=sys.stderr)
        return []
    previous_defaults = read_json(defaults_path) or {}
    current_profiles = existing.get("profiles", {}) if isinstance(existing.get("profiles"), dict) else {}

    contracts: dict[str, dict] = {}
    kit_defaults: dict[str, dict] = {}
    for profile in profiles:
        contract = load_contract(profile)
        kit_commands = contract.get("commands", {})
        kit_root = detect_root(workspace, contract.get("root_markers", []))
        previous_commands, previous_root = previous_kit_values(previous_defaults.get(profile))
        current = current_profiles.get(profile, {})
        current = current if isinstance(current, dict) else {}
        contract["root"] = merge_root(kit_root, previous_root, current.get("root") if isinstance(current.get("root"), str) else None)
        contract["commands"] = merge_commands(
            kit_commands,
            previous_commands,
            current.get("commands") if isinstance(current.get("commands"), dict) else None,
        )
        contracts[profile] = contract
        kit_defaults[profile] = {"commands": kit_commands, "root": kit_root}

    write_json(profiles_path, {"about": ABOUT, "profiles": contracts})
    write_json(defaults_path, kit_defaults)
    return [f"{name} ({contract['root']})" for name, contract in contracts.items()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect AIKit profile contracts into .aikit/profiles.json")
    parser.add_argument("--profiles", required=True, help="profile1+profile2")
    parser.add_argument("--workspace", default=".")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profiles = [item for item in args.profiles.split("+") if item]
    print(", ".join(install(Path(args.workspace).resolve(), profiles)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
