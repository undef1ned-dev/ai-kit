#!/usr/bin/env python3
"""Read and install independently authored Codex agents, skills and role metadata."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parent.parent
NAME = re.compile(r"^[a-z][a-z0-9-]*$")


def layers(profiles: list[str], packs: list[str], root: Path = ROOT) -> list[Path]:
    if any(not NAME.fullmatch(name) for name in [*profiles, *packs]):
        raise ValueError("Invalid profile or pack name")
    return [root / "base", *(root / "profiles" / name for name in profiles), *(root / "packs" / name for name in packs)]


def read_agent(path: Path) -> dict:
    try:
        import tomllib
    except ImportError as error:
        raise ValueError("Native Codex definitions require Python 3.11+") from error

    agent = tomllib.loads(path.read_text(encoding="utf-8"))
    if agent.get("name") != path.stem or not agent.get("description") or not agent.get("developer_instructions"):
        raise ValueError(f"Invalid native Codex agent: {path}")
    if not isinstance(agent.get("model"), str) or agent["model"] in {"opus", "sonnet", "haiku"}:
        raise ValueError(f"Native Codex agent needs a model id: {path}")
    if agent.get("model_reasoning_effort") not in {"low", "medium", "high", "xhigh", "max", "ultra"}:
        raise ValueError(f"Native Codex agent needs an explicit reasoning effort: {path}")
    return agent


def agents(sources: list[Path]) -> dict[str, Path]:
    found = {}
    for source in sources:
        directory = source / "codex/agents"
        if not directory.is_dir():
            raise ValueError(f"Missing native Codex agents: {directory}; no fallback to another runtime")
        for path in sorted(directory.glob("*.toml")):
            read_agent(path)
            if path.stem in found:
                raise ValueError(f"Duplicate Codex agent: {path.stem}")
            found[path.stem] = path
    return found


def skills(sources: list[Path], *, plugin: bool = False) -> list[Path]:
    found = {}
    for source in sources:
        for group in ("skills", "plugin-skills") if plugin else ("skills",):
            directory = source / "codex" / group
            for skill in sorted(directory.glob("*/SKILL.md")):
                if skill.parent.name in found:
                    raise ValueError(f"Duplicate Codex skill: {skill.parent.name}")
                found[skill.parent.name] = skill.parent
    return list(found.values())


def catalog(sources: list[Path]) -> dict:
    result = {"agents": {}, "skills": {}}
    for source in sources:
        path = source / "codex/catalog.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for group in result:
            if not isinstance(data.get(group), dict):
                raise ValueError(f"Invalid Codex catalog section {group}: {path}")
            if result[group].keys() & data[group].keys():
                raise ValueError(f"Duplicate Codex catalog names in {path}")
            result[group].update(data[group])
    return result


def install_agents(sources: list[Path], destination: Path) -> list[str]:
    available = agents(sources)
    destination.mkdir(parents=True, exist_ok=True)
    for name, source in available.items():
        shutil.copyfile(source, destination / f"{name}.toml")
    return list(available)


def write_catalog(sources: list[Path], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes((json.dumps(catalog(sources), ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
