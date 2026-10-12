#!/usr/bin/env python3
"""
Collect the contracts of the installed profiles into one project file: .aikit/profiles.json.

Source of truth: profiles/<profile>/profile.manifest.json. Agents, skills and hooks of every
runtime read the project file, so they do not need to know the kit layout.

The team may edit "commands" in .aikit/profiles.json (another package manager, extra flags,
a removed command). Kit defaults from the previous run are kept in .aikit/profiles.kit-defaults.json:
a command still equal to the old default follows the kit, a changed or removed one stays as the team left it.
Every other field is owned by the kit and refreshed on each run.

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
    "Контракты профилей AIKit: агенты по ролям, специалисты, команды. "
    "Команды в commands можно менять под проект — обновление кита их не затрёт; остальные поля обновляются из кита. "
    "{files} в команде — изменённые файлы."
)


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


def install(workspace: Path, profiles: list[str]) -> list[str]:
    """Write .aikit/profiles.json for the given profiles. Returns the profile names written."""
    profiles_path = workspace / PROFILES_FILE
    defaults_path = workspace / DEFAULTS_FILE
    existing = read_json(profiles_path)
    if existing is None:
        print(f"! {PROFILES_FILE} не разобран как JSON — файл не обновлён, исправь его и повтори установку", file=sys.stderr)
        return []
    previous_defaults = read_json(defaults_path) or {}
    current_profiles = existing.get("profiles", {}) if isinstance(existing.get("profiles"), dict) else {}

    contracts: dict[str, dict] = {}
    kit_defaults: dict[str, dict[str, str]] = {}
    for profile in profiles:
        contract = load_contract(profile)
        kit_commands = contract.get("commands", {})
        current = current_profiles.get(profile, {})
        contract["commands"] = merge_commands(
            kit_commands,
            previous_defaults.get(profile),
            current.get("commands") if isinstance(current, dict) and isinstance(current.get("commands"), dict) else None,
        )
        contracts[profile] = contract
        kit_defaults[profile] = kit_commands

    write_json(profiles_path, {"about": ABOUT, "profiles": contracts})
    write_json(defaults_path, kit_defaults)
    return list(contracts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect AIKit profile contracts into .aikit/profiles.json")
    parser.add_argument("--profiles", required=True, help="profile1+profile2")
    parser.add_argument("--workspace", default=".")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profiles = [item for item in args.profiles.split("+") if item]
    print(" ".join(install(Path(args.workspace).resolve(), profiles)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
