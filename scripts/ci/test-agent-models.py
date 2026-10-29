#!/usr/bin/env python3
"""
Checks of scripts/agent_models.py: tiers of the kit's agents, the tier map of every runtime,
project overrides and how the model lands in Claude Code, Codex and OpenCode agent files.

Usage: python3 scripts/ci/test-agent-models.py
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent_models  # noqa: E402

FAILURES: list[str] = []
FRONTMATTER_EFFORT = re.compile(r"^effort:\s*(\S+)\s*$", re.M)


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"  {'✓' if condition else '✗'} {name}{f' — {detail}' if detail and not condition else ''}")
    if not condition:
        FAILURES.append(name)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    tiers = agent_models.tiers()
    kit = agent_models.kit_models()
    agent_tiers = agent_models.kit_agent_tiers()
    unknown = {name: tier for name, tier in agent_tiers.items() if tier not in tiers}
    check("у каждого агента кита model — уровень из adapters/models.json", not unknown, str(unknown))
    gaps = [f"{runtime}/{tier}" for runtime in agent_models.RUNTIMES for tier in tiers
            if not kit.get("runtimes", {}).get(runtime, {}).get(tier, {}).get("model")]
    check("adapters/models.json: модель для каждого runtime и уровня", not gaps, ", ".join(gaps))
    # Claude Code: effort in the agent's frontmatter overrides the session level — architects high, the rest medium.
    # Like the tier check, only agents that name a model tier are held to it
    efforts = {}
    for pattern in (*agent_models.AGENT_SOURCES, "templates/profile/agents"):
        for path in sorted(agent_models.ROOT.glob(f"{pattern}/*.md")):
            head = path.read_text(encoding="utf-8").split("\n---", 1)[0]
            if not agent_models.FRONTMATTER_MODEL.search(head):
                continue
            match = FRONTMATTER_EFFORT.search(head)
            efforts[path.relative_to(agent_models.ROOT).as_posix()] = match.group(1) if match else None
    wrong = {name: level for name, level in efforts.items() if level != ("high" if name.endswith("architect.md") else "medium")}
    check("effort агентов кита: архитекторы high, остальные medium", bool(efforts) and not wrong, str(wrong))

    opus = kit["runtimes"]["codex"]["opus"]
    check("Codex: default модели берётся из нативного TOML", agent_models.resolve("vue-architect", "opus", "codex", {}) == opus)
    project = {
        "agents": {"vue-coder": "opus", "vue-tester": {"codex": "gpt-test", "claude": "haiku"}},
        "tiers": {"opencode": {"opus": "openrouter/test-opus"}},
    }
    check("переопределение уровнем — модели этого уровня", agent_models.resolve("vue-coder", "sonnet", "codex", project) == opus)
    check("переопределение для runtime — модель как есть", agent_models.resolve("vue-tester", "sonnet", "codex", project) == {"model": "gpt-test", "model_reasoning_effort": "medium"})
    check("runtime без переопределения — уровень агента",
          agent_models.resolve("vue-tester", "sonnet", "opencode", project) == kit["runtimes"]["opencode"]["sonnet"])
    check("проект меняет модель уровня", agent_models.resolve("vue-coder", "sonnet", "opencode", project) == {"model": "openrouter/test-opus"})
    check("неизвестный уровень — модель не задаётся", agent_models.resolve("x", "inherit", "codex", {}) == {})
    architect = {**opus, "model_reasoning_effort": "medium"}
    check("настройка кита для агента: Codex medium вместо high у forge-1-12-java-architect",
          agent_models.resolve("forge-1-12-java-architect", "opus", "codex", {}) == architect)
    check("настройка кита для агента не задевает Claude Code",
          agent_models.resolve("forge-1-12-java-architect", "opus", "claude", {}) == kit["runtimes"]["claude"]["opus"])
    check("переопределение проекта сильнее настройки кита",
          agent_models.resolve("forge-1-12-java-architect", "opus", "codex", {"agents": {"forge-1-12-java-architect": "opus"}}) == opus)

    toml = 'name = "a"\ndescription = "d"\nmodel = "old"\ndeveloper_instructions = """\ntext\n"""\n'
    updated = agent_models.set_toml_fields(toml, {"model": "gpt-6.1-sol", "model_reasoning_effort": "high"})
    check("TOML Codex: модель после description, старая убрана",
          updated.startswith('name = "a"\ndescription = "d"\nmodel = "gpt-6.1-sol"\nmodel_reasoning_effort = "high"\ndeveloper_instructions'), updated)
    markdown = "---\nname: a\nmodel: sonnet\n---\nbody model: x\n"
    check("frontmatter: модель заменена только в шапке",
          agent_models.set_frontmatter_model(markdown, "haiku") == "---\nname: a\nmodel: haiku\n---\nbody model: x\n")
    check("frontmatter без model: модель добавлена",
          agent_models.set_frontmatter_model("---\nname: a\n---\nbody\n", "anthropic/x") == "---\nname: a\nmodel: anthropic/x\n---\nbody\n")

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        agents = workspace / ".claude" / "agents"
        agents.mkdir(parents=True)
        (agents / "vue-coder.md").write_text("---\nname: vue-coder\nmodel: sonnet\neffort: medium\n---\n", encoding="utf-8")
        (agents / "team-own.md").write_text("---\nname: team-own\nmodel: sonnet\n---\n", encoding="utf-8")
        (workspace / ".aikit").mkdir()
        (workspace / ".aikit" / "models.json").write_text(json.dumps({"agents": {"vue-coder": "haiku", "team-own": "opus"}}), encoding="utf-8")
        agent_models.apply("claude", workspace)
        check("apply: агент кита получил модель проекта", "model: haiku" in (agents / "vue-coder.md").read_text(encoding="utf-8"))
        check("apply: effort агента сохранён", "\neffort: medium\n" in (agents / "vue-coder.md").read_text(encoding="utf-8"))
        check("apply: свой агент команды не тронут", "model: sonnet" in (agents / "team-own.md").read_text(encoding="utf-8"))

    if FAILURES:
        print(f"✗ Модели агентов: ошибок — {len(FAILURES)}")
        return 1
    print("✓ Модели агентов")
    return 0


if __name__ == "__main__":
    sys.exit(main())
