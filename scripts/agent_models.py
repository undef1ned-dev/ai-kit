#!/usr/bin/env python3
"""
Models of AIKit agents in every runtime.

Claude/OpenCode frontmatter names a tier: `model: opus | sonnet | haiku`. adapters/models.json maps each tier
to a model per runtime (Claude Code aliases, Codex and OpenCode model ids); its "agents" section adjusts single
fields of one agent on top of the tier ("forge-1-12-java-architect": {"codex": {"model_reasoning_effort": "medium"}}).
Codex defaults come directly from <layer>/codex/agents/*.toml, without reading Markdown.
A project overrides defaults in
.aikit/models.json, which /set-model writes:

    {
      "agents": {
        "vue-coder": "opus",                                   # another tier, in every runtime
        "vue-tester": {"codex": "gpt-6-luna", "claude": "haiku"}  # per runtime: a tier or a model id
      },
      "tiers": {"opencode": {"opus": "openrouter/anthropic/claude-opus-5-5"}}  # remap a tier for this project
    }

`apply` writes the resolved model into the agent files a runtime reads:
    claude   — .claude/agents/*.md (attach.sh); agents from the plugin get the model from the rule in CLAUDE.md;
               only `model:` changes, `effort:` of the agent stays as the kit set it
    codex    — .codex/agents/*.toml: model, model_reasoning_effort
    opencode — .opencode/agents/*.md: model

Usage:
    python3 scripts/agent_models.py apply --runtime codex --workspace .
    python3 scripts/agent_models.py show --runtime codex --workspace .
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT_MODELS = ROOT / "adapters" / "models.json"
PROJECT_MODELS = Path(".aikit") / "models.json"
RUNTIMES = ("claude", "codex", "opencode", "antigravity")
# agents — an adapter install ships this script in .aikit/scripts/ next to the kit agents in .aikit/agents/
AGENT_SOURCES = ("base/agents", "profiles/*/agents", "packs/*/agents", "agents")
FRONTMATTER_MODEL = re.compile(r"^model:\s*(\S+)\s*$", re.M)


def read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def kit_models() -> dict:
    return read_json(KIT_MODELS)


def tiers() -> list[str]:
    return list(kit_models().get("tiers", []))


def kit_agent_tiers() -> dict[str, str]:
    """Agent name → the tier its frontmatter names, over every agent of the kit."""
    found: dict[str, str] = {}
    for pattern in AGENT_SOURCES:
        for path in sorted(ROOT.glob(f"{pattern}/*.md")):
            match = FRONTMATTER_MODEL.search(path.read_text(encoding="utf-8"))
            if match:
                found[path.stem] = match.group(1)
    return found


def codex_defaults() -> dict[str, dict[str, str]]:
    """Codex defaults come from native definitions, never Markdown model tiers."""
    import tomllib

    found = {}
    for pattern in ("base/codex/agents/*.toml", "profiles/*/codex/agents/*.toml", "packs/*/codex/agents/*.toml", "agents/*.toml"):
        for path in ROOT.glob(pattern):
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            found[path.stem] = {key: data[key] for key in ("model", "model_reasoning_effort") if key in data}
    return found


def tier_fields(runtime: str, tier: str, project: dict) -> dict[str, str]:
    remapped = project.get("tiers", {}).get(runtime, {}).get(tier)
    if remapped:
        return {"model": str(remapped)}
    return dict(kit_models().get("runtimes", {}).get(runtime, {}).get(tier, {}))


def kit_agent_fields(agent: str, runtime: str) -> dict[str, str]:
    """Fields the kit sets for one agent on top of its tier, e.g. a lower Codex reasoning effort."""
    return dict(kit_models().get("agents", {}).get(agent, {}).get(runtime, {}))


def resolve(agent: str, tier: str | None, runtime: str, project: dict) -> dict[str, str]:
    """The fields that set the agent's model in this runtime; empty when nothing is known."""
    choice = project.get("agents", {}).get(agent)
    if isinstance(choice, dict):
        choice = choice.get(runtime)
    if isinstance(choice, str) and choice:
        if choice in tiers():
            return tier_fields(runtime, choice, project)
        fields = dict(codex_defaults().get(agent, {})) if runtime == "codex" else {}
        fields["model"] = choice
        return fields
    if runtime == "codex":
        return dict(codex_defaults().get(agent, {}))
    if tier in tiers():
        return {**tier_fields(runtime, tier, project), **kit_agent_fields(agent, runtime)}
    return {}


def set_frontmatter_model(text: str, model: str) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end < 0:
        return text
    head = text[:end]
    if FRONTMATTER_MODEL.search(head):
        head = FRONTMATTER_MODEL.sub(f"model: {model}", head, count=1)
    else:
        head += f"\nmodel: {model}"
    return head + text[end:]


def set_toml_fields(text: str, fields: dict[str, str]) -> str:
    lines = [line for line in text.split("\n") if not re.match(r"^(model|model_reasoning_effort)\s*=", line)]
    at = next((i + 1 for i, line in enumerate(lines) if line.startswith("description =")), 0)
    inserted = [f"{key} = {json.dumps(value, ensure_ascii=False)}" for key, value in fields.items()]
    return "\n".join(lines[:at] + inserted + lines[at:])


def agent_files(runtime: str, workspace: Path) -> list[Path]:
    folder = {
        "claude": ".claude/agents",
        "codex": ".codex/agents",
        "opencode": ".opencode/agents",
        "antigravity": ".agents/agents",
    }[runtime]
    suffix = ".toml" if runtime == "codex" else ".md"
    return sorted((workspace / folder).glob(f"*{suffix}"))


def plan(runtime: str, workspace: Path) -> list[tuple[Path, dict[str, str]]]:
    project = read_json(workspace / PROJECT_MODELS)
    agent_tiers = {name: None for name in codex_defaults()} if runtime == "codex" else kit_agent_tiers()
    result = []
    for path in agent_files(runtime, workspace):
        # Only the kit's agents: a team's own agent in the same folder keeps its model
        if path.stem not in agent_tiers:
            continue
        result.append((path, resolve(path.stem, agent_tiers[path.stem], runtime, project)))
    return result


def apply(runtime: str, workspace: Path) -> int:
    changed = 0
    for path, fields in plan(runtime, workspace):
        if not fields.get("model"):
            continue
        text = path.read_text(encoding="utf-8")
        if runtime == "codex":
            updated = set_toml_fields(text, fields)
        else:
            updated = set_frontmatter_model(text, fields["model"])
        if updated != text:
            path.write_bytes(updated.encode("utf-8"))
            changed += 1
    return changed


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Apply AIKit agent models to a runtime's agent files")
    parser.add_argument("action", choices=("apply", "show"))
    parser.add_argument("--runtime", choices=RUNTIMES, required=True)
    parser.add_argument("--workspace", default=".")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    if args.action == "show":
        for path, fields in plan(args.runtime, workspace):
            print(f"{path.stem}: {', '.join(f'{k}={v}' for k, v in fields.items()) or '—'}")
        return 0
    print(f"Модели агентов ({args.runtime}): обновлено файлов — {apply(args.runtime, workspace)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
