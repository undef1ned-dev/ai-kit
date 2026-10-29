#!/usr/bin/env python3
"""
Build the AIKit plugin marketplace for Claude Code and Codex from the kit sources.

Plugins:
    aikit      — the core: base agents and skills, hooks, base MCP servers and the init skill.
                 Its root is the repository root, so scripts/ and the profile sources travel with it.
    <profile>  — profiles/<profile>/: agents, skills and MCP servers of the stack
    <pack>     — packs/<pack>/: agents, skills and MCP servers of the pack

Output (committed, both runtimes read it straight from the repository):
    .claude-plugin/marketplace.json            — the marketplace; Codex reads this path as well
    .claude-plugin/plugin.json                 — Claude Code manifest of the core plugin
    .codex-plugin/plugin.json                  — Codex manifest of the core plugin
    profiles/*/.claude-plugin/plugin.json, profiles/*/.codex-plugin/plugin.json
    packs/*/.claude-plugin/plugin.json,    packs/*/.codex-plugin/plugin.json

Codex plugins carry skills, hooks and MCP servers but no agents: the init skill writes
.codex/agents/*.toml into the project.

Every manifest and marketplace entry carries "version" from the root VERSION file: Claude Code and Codex
update an installed plugin when this number changes. VERSION is bumped by scripts/bump-version.py on merge.

Usage:
    python3 scripts/build-plugins.py            # write the manifests
    python3 scripts/build-plugins.py --check    # exit 1 if a manifest is out of date or points to a missing file
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import codex_content
import hooks_config
import mcp_config
from release_utils import is_semver

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE_NAME = "aikit"
CORE_PLUGIN = "aikit"
OWNER = {"name": "undef1ned-dev"}
REPO_URL = "https://github.com/undef1ned-dev/ai-kit"
MARKETPLACE_FILE = Path(".claude-plugin") / "marketplace.json"
CLAUDE_MANIFEST = Path(".claude-plugin") / "plugin.json"
CODEX_MANIFEST = Path(".codex-plugin") / "plugin.json"
CORE_SKILL_DIRS = ("base/skills", "base/plugin-skills")
HOOK_SCRIPT = "base/hooks/aikit_hook.py"
# aikit_hook.py with this flag acts only in projects connected to the kit (.aikit/ above the cwd)
PLUGIN_FLAG = "--plugin"
CLAUDE_HOOK_COMMAND = f'python3 "${{CLAUDE_PLUGIN_ROOT}}/{HOOK_SCRIPT}" {PLUGIN_FLAG}'
CODEX_HOOK_COMMAND = f'python3 "${{PLUGIN_ROOT}}/{HOOK_SCRIPT}" {PLUGIN_FLAG}'
# Codex passes PLUGIN_ROOT only as an environment variable, and on Windows the hook shell (powershell
# -Command or cmd.exe) does not expand ${PLUGIN_ROOT}: the launcher of hooks_config reads it without shell syntax
PLUGIN_FIND = f"h = os.path.join(os.environ['PLUGIN_ROOT'], *{HOOK_SCRIPT.split('/')!r})"
CODEX_HOOK_COMMAND_WINDOWS = hooks_config.windows_launcher(PLUGIN_FIND, [PLUGIN_FLAG, hooks_config.DENY_JSON_FLAG])
CORE_DESCRIPTION = (
    "Ядро AIKit: правила команды, агенты планирования и памяти, оркестрация /implement-feature, "
    "хуки (Conventional Commits, секреты, линтер, тесты) и /aikit:setup для подключения проекта."
)
CATEGORY = "development"
VERSION_FILE = ROOT / "VERSION"


def kit_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else ""


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def render_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def mcp_servers(source_dir: Path, render) -> dict:
    config_path = source_dir / "mcp.json"
    if not config_path.exists():
        return {}
    servers = read_json(config_path).get("servers", {})
    return {name: render(server) for name, server in servers.items()}


def render_codex_mcp(server: dict) -> dict:
    if "url" in server:
        return {"url": server["url"]}
    rendered = {"command": server["command"], "args": server.get("args", [])}
    if server.get("env_vars"):
        rendered["env_vars"] = server["env_vars"]
    return rendered


def plugin_specs() -> list[dict]:
    """Every plugin of the marketplace: name, folder relative to the root and description."""
    specs = [{"name": CORE_PLUGIN, "dir": Path("."), "label": "AIKit", "description": CORE_DESCRIPTION, "core": True}]
    for manifest in sorted((ROOT / "profiles").glob("*/profile.manifest.json")):
        contract = read_json(manifest)
        specs.append({
            "name": contract["profile"],
            "dir": manifest.parent.relative_to(ROOT),
            "label": f"AIKit: {contract['label']}",
            "description": f"Профиль AIKit {contract['label']} ({contract['stack']}): агенты architect → coder → tester → reviewer, скиллы и MCP стека.",
            "core": False,
        })
    for manifest in sorted((ROOT / "packs").glob("*/pack.json")):
        pack = read_json(manifest)
        specs.append({
            "name": pack["name"],
            "dir": manifest.parent.relative_to(ROOT),
            "label": f"AIKit: {pack['label']}",
            "description": f"{pack['label']} для AIKit — {pack['description']}",
            "core": False,
        })
    return specs


def relative_source(folder: Path) -> str:
    return "./" if folder == Path(".") else f"./{folder.as_posix()}"


def keywords(spec: dict) -> list[str]:
    return list(dict.fromkeys(["aikit", spec["name"]]))


def event_lists(groups: dict[str, dict]) -> dict[str, list[dict]]:
    """hooks_config gives one handler group per event; hook configs hold a list of groups per event."""
    return {event: [group] for event, group in groups.items()}


def core_agents() -> list[str]:
    return [f"./base/agents/{path.name}" for path in sorted((ROOT / "base" / "agents").glob("*.md"))]


def claude_manifest(spec: dict) -> dict:
    source_dir = ROOT / spec["dir"]
    manifest: dict = {
        "name": spec["name"],
        "version": kit_version(),
        "description": spec["description"],
        "author": OWNER,
        "homepage": REPO_URL,
        "repository": REPO_URL,
        "keywords": keywords(spec),
    }
    if spec["core"]:
        manifest["skills"] = [f"./{folder}/" for folder in CORE_SKILL_DIRS]
        manifest["agents"] = core_agents()
        manifest["hooks"] = event_lists(hooks_config.claude_groups(CLAUDE_HOOK_COMMAND))
        source_dir = ROOT / "base"
    servers = mcp_servers(source_dir, mcp_config.render_claude)
    if servers:
        manifest["mcpServers"] = servers
    return manifest


def codex_manifest(spec: dict) -> dict:
    source_dir = ROOT / spec["dir"]
    manifest: dict = {
        "name": spec["name"],
        "version": kit_version(),
        "description": spec["description"],
        "keywords": keywords(spec),
    }
    if (source_dir / "codex/skills").is_dir():
        manifest["skills"] = "./codex/skills/"
    if spec["core"]:
        manifest["skills"] = ["./base/codex/skills/", "./base/codex/plugin-skills/"]
        manifest["hooks"] = {"hooks": event_lists(hooks_config.codex_groups(CODEX_HOOK_COMMAND, CODEX_HOOK_COMMAND_WINDOWS))}
        source_dir = ROOT / "base"
    servers = mcp_servers(source_dir, render_codex_mcp)
    if servers:
        manifest["mcpServers"] = servers
    manifest["interface"] = {
        "displayName": spec["label"],
        "shortDescription": spec["description"],
        "developerName": OWNER["name"],
        "category": "Coding",
        "websiteURL": REPO_URL,
    }
    return manifest


def marketplace(specs: list[dict]) -> dict:
    return {
        "name": MARKETPLACE_NAME,
        "owner": OWNER,
        "description": "AIKit — агенты, скиллы, хуки и MCP для команд Vue/Nuxt и других стеков по контракту профиля.",
        "plugins": [
            {
                "name": spec["name"],
                "source": relative_source(spec["dir"]),
                "version": kit_version(),
                "description": spec["description"],
                "category": CATEGORY,
            }
            for spec in specs
        ],
    }


def expected_files() -> dict[Path, str]:
    specs = plugin_specs()
    files = {ROOT / MARKETPLACE_FILE: render_json(marketplace(specs))}
    for spec in specs:
        folder = ROOT / spec["dir"]
        files[folder / CLAUDE_MANIFEST] = render_json(claude_manifest(spec))
        files[folder / CODEX_MANIFEST] = render_json(codex_manifest(spec))
    return files


def broken_references() -> list[str]:
    """Paths the manifests point to must exist, and every skill folder must hold a SKILL.md."""
    problems = []
    for spec in plugin_specs():
        folder = ROOT / spec["dir"]
        skill_dirs = [ROOT / path for path in CORE_SKILL_DIRS] if spec["core"] else [folder / "skills"]
        for skill_dir in skill_dirs:
            if not skill_dir.is_dir():
                if spec["core"]:
                    problems.append(f"{spec['name']}: нет папки скиллов {skill_dir.relative_to(ROOT).as_posix()}")
                continue
            problems += [
                f"{spec['name']}: в {path.relative_to(ROOT).as_posix()} нет SKILL.md"
                for path in sorted(skill_dir.iterdir())
                if path.is_dir() and not (path / "SKILL.md").exists()
            ]
        try:
            layer = ROOT / "base" if spec["core"] else folder
            codex_content.agents([layer])
            codex_content.catalog([layer])
            codex_content.skills([layer], plugin=True)
        except (OSError, ValueError) as error:
            problems.append(str(error))
        if not spec["core"] and not (folder / "agents").is_dir():
            problems.append(f"{spec['name']}: нет папки агентов")
    if not (ROOT / HOOK_SCRIPT).exists():
        problems.append(f"нет скрипта хуков {HOOK_SCRIPT}")
    if not is_semver(kit_version()):
        problems.append(f"в VERSION не semver X.Y.Z: «{kit_version()}»")
    return problems


def version_mismatches(files: dict[Path, str]) -> list[str]:
    """Manifests whose "version" differs from VERSION: plugins would not update, or update to the wrong number."""
    problems = []
    for path in files:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        entries = data.get("plugins", []) if path.name == MARKETPLACE_FILE.name else [data]
        for entry in entries:
            if isinstance(entry, dict) and entry.get("version") != kit_version():
                name = entry.get("name", "?")
                problems.append(
                    f"{path.relative_to(ROOT).as_posix()}: версия {name} «{entry.get('version', '')}» не равна VERSION «{kit_version()}»"
                )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the AIKit plugin marketplace for Claude Code and Codex")
    parser.add_argument("--check", action="store_true", help="do not write; exit 1 if a manifest is out of date")
    args = parser.parse_args()

    problems = broken_references()
    files = expected_files()
    if args.check:
        problems += version_mismatches(files)
        stale = [path for path, content in files.items() if not path.exists() or path.read_text(encoding="utf-8") != content]
        problems += [f"устарел {path.relative_to(ROOT).as_posix()} — запусти python3 scripts/build-plugins.py" for path in stale]
    else:
        for path, content in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
        print(f"Плагинов: {len(plugin_specs())}, файлов: {len(files)}")
    for problem in problems:
        print(f"  ✗ {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
