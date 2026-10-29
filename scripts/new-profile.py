#!/usr/bin/env python3
"""
Create a new AIKit profile from templates/profile/: contract, rules, four role agents, quality specialist, settings.

The kit core (installers, /implement-feature) reads everything it needs from
profile.manifest.json, so a new stack needs no changes outside profiles/<name>/.
See docs/guide/adding-a-stack.md.

Usage:
    python3 scripts/new-profile.py java-spring --role backend --stack "Java 21, Spring Boot 3" \\
        --test "./mvnw test" --lint "./mvnw checkstyle:check" --root-marker pom.xml --path-signal src/main/java/ \
        --code-extension .java
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "templates" / "profile"
ROLES = ("architect", "coder", "tester", "reviewer")
# Every profile ships a quality specialist for /coverage-check and /tech-debt
QUALITY_TEMPLATE = "quality-analyst"
QUALITY_WHEN = "нужна оценка покрытия тестами или технического долга (/coverage-check, /tech-debt)"
COMMANDS = ("install", "lint", "format", "test", "build", "run")
ROLE_TEXT = {"backend": "backend-разработки", "web": "frontend-разработки"}
ROLE_SCOPE = {"backend": "BACKEND SCOPE", "web": "WEB SCOPE"}
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a new AIKit profile from templates/profile/")
    parser.add_argument("name", help="profile name, e.g. java-spring")
    parser.add_argument("--role", required=True, help="part of the system: backend, web, mobile, ...")
    parser.add_argument("--stack", required=True, help='e.g. "Java 21, Spring Boot 3, JUnit 5"')
    parser.add_argument("--label", help="human-readable name; default: from the profile name")
    parser.add_argument("--prefix", help="agent name prefix; default: the last part of the profile name")
    for command in COMMANDS:
        parser.add_argument(f"--{command}", required=command == "test", help=f"{command} command ({{files}} = changed files)")
    parser.add_argument("--root-marker", action="append", required=True, help="file that marks the profile folder, e.g. pom.xml")
    parser.add_argument("--path-signal", action="append", required=True, help="path inside the profile folder, e.g. src/main/java/")
    parser.add_argument("--code-extension", action="append", default=[], help="code file extension for hooks, e.g. .java; default: every file")
    return parser.parse_args()


def fail(message: str) -> None:
    print(f"Ошибка: {message}", file=sys.stderr)
    raise SystemExit(1)


def existing_agent_names() -> set[str]:
    return {path.stem for path in ROOT.glob("*/agents/*.md")} | {path.stem for path in ROOT.glob("*/*/agents/*.md")}


def render(text: str, variables: dict[str, str]) -> str:
    for key, value in variables.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def main() -> int:
    args = parse_args()
    name = args.name
    if not NAME_PATTERN.match(name):
        fail(f"имя профиля '{name}': только латиница в нижнем регистре, цифры и дефисы")
    profile_dir = ROOT / "profiles" / name
    if profile_dir.exists():
        fail(f"профиль {name} уже есть: {profile_dir}")
    prefix = args.prefix or name.split("-")[-1]
    agents = {role: f"{prefix}-{role}" for role in ROLES}
    quality_agent = f"{prefix}-{QUALITY_TEMPLATE}"
    taken = sorted({*agents.values(), quality_agent} & existing_agent_names())
    if taken:
        fail(f"агенты {taken} уже есть в ките — задай другой --prefix")
    bad_extensions = [item for item in args.code_extension if not item.startswith(".")]
    if bad_extensions:
        fail(f"расширения {bad_extensions} должны начинаться с точки: .java")

    commands = {command: getattr(args, command) for command in COMMANDS if getattr(args, command)}
    label = args.label or " ".join(part.capitalize() for part in name.split("-"))
    variables = {
        "PROFILE": name,
        "PREFIX": prefix,
        "LABEL": label,
        "ROLE": args.role,
        "ROLE_TEXT": ROLE_TEXT.get(args.role, f"{args.role}-разработки"),
        "ROLE_SCOPE": ROLE_SCOPE.get(args.role, "scope своей части"),
        "STACK": args.stack,
    }

    profile_dir.mkdir(parents=True)
    (profile_dir / "agents").mkdir()
    for template, agent in [*agents.items(), (QUALITY_TEMPLATE, quality_agent)]:
        text = (TEMPLATE_DIR / "agents" / f"{template}.md").read_text(encoding="utf-8")
        (profile_dir / "agents" / f"{agent}.md").write_text(render(text, variables), encoding="utf-8", newline="\n")
    rules = (TEMPLATE_DIR / "RULES.md").read_text(encoding="utf-8")
    (profile_dir / "RULES.md").write_text(render(rules, variables), encoding="utf-8", newline="\n")

    # Claude Code asks before every unknown command; the profile allows its own tools up front
    settings = json.loads((TEMPLATE_DIR / "settings.json").read_text(encoding="utf-8"))
    tools = sorted({command.split()[0] for command in commands.values()})
    settings["permissions"]["allow"] = [f"Bash({tool} *)" for tool in tools]
    (profile_dir / "settings.json").write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    manifest = {
        "profile": name,
        "label": label,
        "role": args.role,
        "stack": args.stack,
        "agents": agents,
        "specialists": {"quality": {"agent": quality_agent, "when": QUALITY_WHEN}},
        "pipelines": {},
        "commands": commands,
        **({"code_extensions": args.code_extension} if args.code_extension else {}),
        "root_markers": args.root_marker,
        "path_signals": args.path_signal,
    }
    (profile_dir / "profile.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    # The profile is also a plugin of the marketplace: its manifests are generated from the sources
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "build-plugins.py")], check=True, stdout=subprocess.DEVNULL)

    print(f"Профиль {name} создан в profiles/{name}/, плагин {name} добавлен в .claude-plugin/marketplace.json")
    print("  Дальше: заполни TODO в RULES.md и агентах, пересобери сайт python3 scripts/generate-docs.py,")
    print("  проверь bash scripts/ci/static-checks.sh,")
    print(f"  подключи к проекту: bash scripts/attach.sh {name}  (или вместе с другими: <web-профиль>+{name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
