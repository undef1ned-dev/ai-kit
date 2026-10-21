#!/usr/bin/env python3
"""
Checks of scripts/agent_models.py: tiers of the kit's agents, the tier map of every runtime,
project overrides and how the model lands in Claude Code, Codex and OpenCode agent files.

Usage: python3 scripts/ci/test-agent-models.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent_models  # noqa: E402

FAILURES: list[str] = []


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

    opus = kit["runtimes"]["codex"]["opus"]
    check("уровень агента берётся из frontmatter", agent_models.resolve("vue-architect", "opus", "codex", {}) == opus)
    project = {
        "agents": {"vue-coder": "opus", "vue-tester": {"codex": "gpt-test", "claude": "haiku"}},
        "tiers": {"opencode": {"opus": "openrouter/test-opus"}},
    }
    check("переопределение уровнем — модели этого уровня", agent_models.resolve("vue-coder", "sonnet", "codex", project) == opus)
    check("переопределение для runtime — модель как есть", agent_models.resolve("vue-tester", "sonnet", "codex", project) == {"model": "gpt-test"})
    check("runtime без переопределения — уровень агента",
          agent_models.resolve("vue-tester", "sonnet", "opencode", project) == kit["runtimes"]["opencode"]["sonnet"])
    check("проект меняет модель уровня", agent_models.resolve("vue-coder", "sonnet", "opencode", project) == {"model": "openrouter/test-opus"})
    check("неизвестный уровень — модель не задаётся", agent_models.resolve("x", "inherit", "codex", {}) == {})

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
        (agents / "vue-coder.md").write_text("---\nname: vue-coder\nmodel: sonnet\n---\n", encoding="utf-8")
        (agents / "team-own.md").write_text("---\nname: team-own\nmodel: sonnet\n---\n", encoding="utf-8")
        (workspace / ".aikit").mkdir()
        (workspace / ".aikit" / "models.json").write_text(json.dumps({"agents": {"vue-coder": "haiku", "team-own": "opus"}}), encoding="utf-8")
        agent_models.apply("claude", workspace)
        check("apply: агент кита получил модель проекта", "model: haiku" in (agents / "vue-coder.md").read_text(encoding="utf-8"))
        check("apply: свой агент команды не тронут", "model: sonnet" in (agents / "team-own.md").read_text(encoding="utf-8"))

    if FAILURES:
        print(f"✗ Модели агентов: ошибок — {len(FAILURES)}")
        return 1
    print("✓ Модели агентов")
    return 0


if __name__ == "__main__":
    sys.exit(main())
