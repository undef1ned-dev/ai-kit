#!/usr/bin/env python3
"""Compose project rules from shared policy and independent runtime instructions."""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES_FILES = {"claude": "CLAUDE.md", "codex": "AGENTS.md", "opencode": "AGENTS.md"}
BEGIN = "<!-- BEGIN AIKIT — managed by AIKit installer, edits inside this block are overwritten -->"
END = "<!-- END AIKIT -->"


def render_rules(runtime: str, profiles: list[str], *, repository: bool = False, root: Path = ROOT) -> str:
    if runtime not in RULES_FILES:
        raise ValueError(f"Unknown runtime: {runtime}")
    sources = [root / "base" / "RULES.md"]
    for profile in profiles:
        if Path(profile).name != profile or profile in {".", ".."} or "\\" in profile:
            raise ValueError(f"Invalid profile: {profile}")
        sources.append(root / "profiles" / profile / "RULES.md")
    sources.append(root / "adapters" / runtime / "rules.md")
    chunks = [path.read_text(encoding="utf-8").strip() for path in sources]
    if repository:
        chunks.append(
            "## Разработка репозитория AIKit\n\n"
            "Этот репозиторий содержит исходники кита, а не проект-потребитель. "
            "Процесс разработки — в `docs/guide/developing-aikit.md`; прочитай его перед правками. "
            "Для сопровождения используй скилл `improve-aikit` и локального агента `aikit-maintainer`. "
            "Правила стека сюда не добавляй. Коммит — только по запросу пользователя.\n\n"
            "Этот файл собирается `scripts/rules.py --repository`: общие правила — в `base/RULES.md`, "
            f"инструкции runtime — в `adapters/{runtime}/rules.md`. Изменяй источники и пересобирай файл."
        )
    return "\n\n---\n\n".join(chunks) + "\n"


def render_block(runtime: str, profiles: list[str]) -> str:
    return f"{BEGIN}\n{render_rules(runtime, profiles)}{END}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", choices=RULES_FILES)
    parser.add_argument("--profiles", default="", help="profile1+profile2")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repository", action="store_true", help="build root CLAUDE.md and AGENTS.md")
    parser.add_argument("--check", action="store_true", help="check root rules without writing")
    args = parser.parse_args()
    if args.repository:
        if args.runtime or args.profiles or args.output:
            parser.error("--repository cannot be combined with --runtime, --profiles or --output")
        failed = False
        for runtime in ("claude", "codex"):
            path = ROOT / RULES_FILES[runtime]
            content = render_rules(runtime, [], repository=True)
            if args.check:
                if not path.exists() or path.read_text(encoding="utf-8") != content:
                    print(f"{path.name} is stale: run python3 scripts/rules.py --repository")
                    failed = True
            else:
                path.write_bytes(content.encode("utf-8"))
        return int(failed)
    if not args.runtime or not args.output or args.check:
        parser.error("use --runtime and --output, or --repository [--check]")
    content = render_rules(args.runtime, [name for name in args.profiles.split("+") if name])
    args.output.write_bytes(content.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
