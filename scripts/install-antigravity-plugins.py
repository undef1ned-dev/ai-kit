#!/usr/bin/env python3
"""
Build and install AIKit plugins for Google Antigravity (Antigravity 2.0, IDE, CLI).

Antigravity discovers global plugins in ~/.gemini/config/plugins/<plugin-name>/.
Each installed plugin is a self-contained bundle with:
    plugin.json                      — Antigravity plugin manifest
    .antigravity-plugin/plugin.json  — multi-provider manifest copy
    skills/<name>/SKILL.md           — skills in Agent Skills format
    agents/<name>.md                 — subagents with Antigravity frontmatter
    mcp_config.json                  — MCP servers (when the layer defines mcp.json)
    hooks.json                       — AIKit hooks (in the core 'aikit' plugin)

The core 'aikit' plugin also ships the kit runtime files (VERSION, base/, profiles/,
packs/, presets/, adapters/, scripts/) so /setup, /update-agents and hooks work
self-contained from ~/.gemini/config/plugins/aikit/ in any project.

Usage:
    python3 scripts/install-antigravity-plugins.py --all
    python3 scripts/install-antigravity-plugins.py --profiles vue-nuxt [--packs devops]
    python3 scripts/install-antigravity-plugins.py --preset frontend-team
    python3 scripts/install-antigravity-plugins.py --workspace .
    python3 scripts/install-antigravity-plugins.py --all --target-dir /tmp/agy-plugins
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
from pathlib import Path

import agent_models
import hooks_config
import mcp_config
import preset_utils

ROOT = Path(__file__).resolve().parent.parent
CORE_PLUGIN = "aikit"
DEFAULT_PLUGINS_DIR = Path.home() / ".gemini" / "config" / "plugins"
STATE_FILE = Path(".aikit") / "plugin-init.json"
CORE_SKILL_DIRS = ("base/skills", "base/plugin-skills")
ARGUMENTS_PLACEHOLDER = "(задача из запроса пользователя)"
RULES_FILE_REFERENCE = re.compile(r"(?<![\w/.-])CLAUDE\.md")
KIT_RUNTIME_DIRS = ("base", "profiles", "packs", "presets", "adapters")


def load_build_plugins():
    path = ROOT / "scripts" / "build-plugins.py"
    spec = importlib.util.spec_from_file_location("aikit_build_plugins", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Не удалось загрузить {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def split_frontmatter(text: str) -> tuple[str, str]:
    match = re.match(r"^---[ \t]*\r?\n(.*?\r?\n)---[ \t]*\r?\n?", text, re.DOTALL)
    if not match:
        return "", text
    return match.group(1), text[match.end() :]


def parse_frontmatter(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([\w][\w-]*):\s*(.*)", line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        result[key] = value
    return result


def frontmatter_document(fields: dict[str, object], body: str) -> str:
    lines = ["---", *(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in fields.items()), "---", ""]
    return "\n".join(lines) + body.lstrip("\n")


def rewrite_antigravity_body(text: str) -> str:
    lines = [
        line if "AGENTS.md" in line else RULES_FILE_REFERENCE.sub("AGENTS.md", line)
        for line in text.split("\n")
    ]
    updated = "\n".join(lines)
    replacements = {
        ".claude/agents/": ".agents/agents/",
        ".claude/skills/": ".agents/skills/",
        ".claude/memory/": ".aikit/memory/",
        ".claude-config/": ".aikit-config/",
    }
    for old, new in replacements.items():
        updated = updated.replace(old, new)
    return updated


def convert_agent_markdown(source: Path, model: str | None = None) -> str:
    raw, body = split_frontmatter(source.read_text(encoding="utf-8"))
    metadata = parse_frontmatter(raw)
    description = metadata.get("description", "").strip() or f"AIKit agent {source.stem}"
    tier = metadata.get("model", "").strip()
    resolved_model = model
    if not resolved_model:
        fields = agent_models.resolve(source.stem, tier, "antigravity", {})
        resolved_model = fields.get("model", "pro")
    frontmatter: dict[str, object] = {
        "name": source.stem,
        "description": description,
        "subagent": True,
        "model": resolved_model,
    }
    return frontmatter_document(frontmatter, rewrite_antigravity_body(body))


def install_workspace_agents(
    workspace: Path,
    profiles: list[str],
    packs: list[str],
    previous: list[str],
) -> list[str]:
    """Write managed Antigravity subagents into <workspace>/.agents/agents/*.md and apply project models."""
    agents_dir = workspace / ".agents" / "agents"
    sources = [
        ROOT / "base",
        *(ROOT / "profiles" / name for name in profiles),
        *(ROOT / "packs" / name for name in packs),
    ]
    available: dict[str, Path] = {}
    for layer in sources:
        for path in sorted((layer / "agents").glob("*.md")):
            available[path.stem] = path

    for name in set(previous) - available.keys():
        (agents_dir / f"{name}.md").unlink(missing_ok=True)

    agents_dir.mkdir(parents=True, exist_ok=True)
    for name, path in available.items():
        (agents_dir / f"{name}.md").write_text(
            convert_agent_markdown(path),
            encoding="utf-8",
            newline="\n",
        )
    agent_models.apply("antigravity", workspace)
    return list(available)


def clear_tree_contents(directory: Path) -> None:
    """Remove files inside directory without failing if Windows holds a watcher handle on a folder."""
    if not directory.exists():
        return
    for path in sorted(directory.rglob("*"), reverse=True):
        if path.is_file() or path.is_symlink():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass


def install_skill(source: Path, destination: Path) -> None:
    clear_tree_contents(destination)
    shutil.copytree(source, destination, dirs_exist_ok=True)
    skill_file = destination / "SKILL.md"
    raw, body = split_frontmatter(skill_file.read_text(encoding="utf-8"))
    metadata = parse_frontmatter(raw)
    description = metadata.get("description", "").strip()
    body = rewrite_antigravity_body(body.replace("$ARGUMENTS", ARGUMENTS_PLACEHOLDER))
    skill_file.write_text(
        frontmatter_document({"name": destination.name, "description": description}, body),
        encoding="utf-8",
        newline="\n",
    )


def copy_kit_runtime_into_core(plugin_dir: Path) -> None:
    """Copy kit sources needed by /setup, /update-agents and hooks into the core 'aikit' plugin bundle."""
    if plugin_dir.resolve() == ROOT.resolve():
        return
    shutil.copyfile(ROOT / "VERSION", plugin_dir / "VERSION")
    for folder_name in KIT_RUNTIME_DIRS:
        src = ROOT / folder_name
        dst = plugin_dir / folder_name
        clear_tree_contents(dst)
        shutil.copytree(
            src,
            dst,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            dirs_exist_ok=True,
        )
    scripts_dst = plugin_dir / "scripts"
    clear_tree_contents(scripts_dst)
    scripts_dst.mkdir(parents=True, exist_ok=True)
    for item in sorted((ROOT / "scripts").iterdir()):
        if item.name in {"ci", "__pycache__"}:
            continue
        if item.is_file():
            shutil.copy2(item, scripts_dst / item.name)


def build_plugin_bundle(spec: dict, target_root: Path, manifest: dict) -> Path:
    plugin_dir = target_root / spec["name"]
    in_place = plugin_dir.resolve() == ROOT.resolve()
    if not in_place:
        clear_tree_contents(plugin_dir)
    plugin_dir.mkdir(parents=True, exist_ok=True)

    write_json(plugin_dir / "plugin.json", manifest)
    write_json(plugin_dir / ".antigravity-plugin" / "plugin.json", manifest)

    source_dir = ROOT / spec["dir"]
    skill_roots = [ROOT / folder for folder in CORE_SKILL_DIRS] if spec["core"] else [source_dir / "skills"]
    skills_dst = plugin_dir / "skills"
    for skill_root in skill_roots:
        if not skill_root.is_dir():
            continue
        for skill_folder in sorted(path.parent for path in skill_root.glob("*/SKILL.md")):
            install_skill(skill_folder, skills_dst / skill_folder.name)

    agents_src = (ROOT / "base" / "agents") if spec["core"] else (source_dir / "agents")
    if agents_src.is_dir():
        agents_dst = plugin_dir / "agents"
        agents_dst.mkdir(parents=True, exist_ok=True)
        for agent_file in sorted(agents_src.glob("*.md")):
            (agents_dst / agent_file.name).write_text(
                convert_agent_markdown(agent_file),
                encoding="utf-8",
                newline="\n",
            )

    mcp_source = (ROOT / "base") if spec["core"] else source_dir
    mcp_path = mcp_source / "mcp.json"
    if mcp_path.is_file():
        servers = read_json(mcp_path).get("servers", {})
        if servers:
            write_json(
                plugin_dir / "mcp_config.json",
                {"mcpServers": {name: mcp_config.render_antigravity(cfg) for name, cfg in servers.items()}},
            )

    if spec["core"]:
        copy_kit_runtime_into_core(plugin_dir)
        write_json(
            plugin_dir / "hooks.json",
            {"aikit": hooks_config.antigravity_groups(hooks_config.ANTIGRAVITY_PLUGIN_SCRIPT, [hooks_config.PLUGIN_FLAG])},
        )

    return plugin_dir


def resolve_plugin_names(args: argparse.Namespace, specs_by_name: dict[str, dict]) -> list[str]:
    if args.all:
        return list(specs_by_name)

    profiles: list[str] = []
    packs: list[str] = []
    if args.preset:
        preset = preset_utils.resolve_preset(args.preset)
        profiles, packs = preset["profiles"], preset["packs"]
    elif args.profiles:
        profiles = [item.strip() for item in args.profiles.split("+") if item.strip()]
    if args.packs:
        packs = list(dict.fromkeys([*packs, *args.packs.split()]))

    if not profiles and not packs:
        workspace = Path(args.workspace).resolve()
        state = read_json(workspace / STATE_FILE)
        profiles = [name for name in state.get("profiles", []) if isinstance(name, str)]
        packs = [name for name in state.get("packs", []) if isinstance(name, str)]

    selected = [CORE_PLUGIN, *profiles, *packs]
    unknown = [name for name in selected if name not in specs_by_name]
    if unknown:
        raise SystemExit(f"Неизвестные плагины: {', '.join(unknown)}")
    return list(dict.fromkeys(selected))


def parse_args() -> argparse.Namespace:
    default_target = os.environ.get("AIKIT_ANTIGRAVITY_PLUGINS_DIR") or str(DEFAULT_PLUGINS_DIR)
    parser = argparse.ArgumentParser(description="Build and install AIKit plugins for Antigravity")
    parser.add_argument("--all", action="store_true", help="install core + all profile and pack plugins")
    parser.add_argument("--profiles", help="profile1+profile2")
    parser.add_argument("--preset", help="preset name from presets/")
    parser.add_argument("--packs", default="", help='extra packs: "devops"')
    parser.add_argument("--workspace", default=".", help="project workspace (reads .aikit/plugin-init.json when no selection flags are given)")
    parser.add_argument("--target-dir", default=default_target, help="Antigravity plugins directory (default: ~/.gemini/config/plugins)")
    return parser.parse_args()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parse_args()
    build_plugins = load_build_plugins()
    specs = build_plugins.plugin_specs()
    specs_by_name = {spec["name"]: spec for spec in specs}
    selected = resolve_plugin_names(args, specs_by_name)
    target_root = Path(args.target_dir).expanduser().resolve()
    target_root.mkdir(parents=True, exist_ok=True)

    installed: list[str] = []
    for name in selected:
        spec = specs_by_name[name]
        manifest = build_plugins.antigravity_manifest(spec)
        build_plugin_bundle(spec, target_root, manifest)
        installed.append(name)

    print(f"Плагины Antigravity ({target_root}): {', '.join(installed)} (v{build_plugins.kit_version()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
