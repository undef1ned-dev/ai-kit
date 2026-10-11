#!/usr/bin/env python3
"""
Install AIKit Codex command surface into local Codex runtime directories.

This script treats `.codex/commands/*.md` as source-of-truth and syncs:
1) `~/.codex/prompts/*.md` for slash command discovery in Codex;
2) `~/.codex/skills/*/SKILL.md` as optional mirrors for command semantics.

Usage:
    python3 scripts/install-codex-command-surface.py
    python3 scripts/install-codex-command-surface.py --prompts-target /tmp/codex-prompts --skills-target /tmp/codex-skills
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / ".codex" / "commands"
BUILTIN_COMMANDS = {"help", "exit", "clear", "compact"}


@dataclass(frozen=True)
class CommandSpec:
    name: str
    source_path: Path
    content: str
    description: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install AIKit Codex command surface into ~/.codex runtime directories")
    parser.add_argument(
        "--source",
        default=str(DEFAULT_SOURCE),
        help="path to source command markdown files (default: .codex/commands in this repository)",
    )
    parser.add_argument(
        "--prompts-target",
        default="~/.codex/prompts",
        help="target path for Codex slash prompt files",
    )
    parser.add_argument(
        "--skills-target",
        default="~/.codex/skills",
        help="target path for Codex skill mirrors",
    )
    parser.add_argument(
        "--skills-prefix",
        default="aikit-command-",
        help="folder prefix for generated skill mirrors",
    )
    parser.add_argument("--no-prompts", action="store_true", help="skip sync into prompts target")
    parser.add_argument("--no-skills", action="store_true", help="skip sync into skills target")
    return parser.parse_args()


def extract_command_name(content: str, source_path: Path) -> str:
    match = re.search(r"(?m)^\s*#\s*/([a-z0-9]+(?:-[a-z0-9]+)*)\s*$", content)
    if match:
        return match.group(1)
    return source_path.stem


def extract_description(content: str) -> str:
    lines = content.splitlines()
    start = 0
    for i, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            start = i + 1
            break
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower() in {"usage:", "rules:", "input:"}:
            continue
        if stripped.startswith("- "):
            continue
        return stripped
    return "AIKit command mirror for Codex."


def load_commands(source_dir: Path) -> list[CommandSpec]:
    if not source_dir.exists():
        raise SystemExit(f"Source directory not found: {source_dir}")

    command_specs: list[CommandSpec] = []
    seen_names: set[str] = set()
    for source_path in sorted(source_dir.glob("*.md")):
        content = source_path.read_text(encoding="utf-8")
        name = extract_command_name(content, source_path)
        if name in seen_names:
            raise SystemExit(f"Duplicate command name detected in source: /{name}")
        if name in BUILTIN_COMMANDS:
            raise SystemExit(f"Command name /{name} collides with built-in Codex command")
        seen_names.add(name)
        command_specs.append(
            CommandSpec(
                name=name,
                source_path=source_path,
                content=content,
                description=extract_description(content),
            )
        )
    if not command_specs:
        raise SystemExit(f"No command markdown files found in {source_dir}")
    return command_specs


def render_skill_markdown(command: CommandSpec) -> str:
    escaped_description = command.description.replace('"', '\\"')
    return (
        f'---\nname: "{command.name}"\ndescription: "{escaped_description}"\n---\n\n'
        f"# AIKit Command Mirror: /{command.name}\n\n"
        "Use this skill when the user explicitly invokes this AIKit command semantics.\n\n"
        f"Treat the text after `/{command.name}` as command arguments.\n\n"
        "Canonical command contract:\n\n"
        "```md\n"
        f"{command.content.rstrip()}\n"
        "```\n"
    )


def sync_prompts(commands: list[CommandSpec], prompts_target: Path) -> list[Path]:
    prompts_target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for command in commands:
        destination = prompts_target / f"{command.name}.md"
        destination.write_text(command.content.rstrip() + "\n", encoding="utf-8")
        written.append(destination)
    return written


def sync_skills(commands: list[CommandSpec], skills_target: Path, skills_prefix: str) -> list[Path]:
    skills_target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for command in commands:
        folder_name = f"{skills_prefix}{command.name}"
        skill_dir = skills_target / folder_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        destination = skill_dir / "SKILL.md"
        destination.write_text(render_skill_markdown(command), encoding="utf-8")
        written.append(destination)
    return written


def print_summary(commands: list[CommandSpec], prompts_written: list[Path], skills_written: list[Path]) -> None:
    print("Installed Codex command surface:")
    print(f"- Commands: {', '.join(f'/{command.name}' for command in commands)}")
    print(f"- Prompt files: {len(prompts_written)}")
    for path in prompts_written:
        print(f"  - {path}")
    print(f"- Skill mirrors: {len(skills_written)}")
    for path in skills_written:
        print(f"  - {path}")
    print("Next step: start a new Codex session so slash prompt discovery refreshes.")


def main() -> int:
    args = parse_args()
    source_dir = Path(args.source).expanduser().resolve()
    prompts_target = Path(args.prompts_target).expanduser().resolve()
    skills_target = Path(args.skills_target).expanduser().resolve()

    commands = load_commands(source_dir)
    prompts_written: list[Path] = []
    skills_written: list[Path] = []

    if not args.no_prompts:
        prompts_written = sync_prompts(commands, prompts_target)
    if not args.no_skills:
        skills_written = sync_skills(commands, skills_target, args.skills_prefix)

    print_summary(commands, prompts_written, skills_written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
