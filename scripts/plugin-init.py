#!/usr/bin/env python3
"""
Connect a project to AIKit installed as plugins (Claude Code or Codex).

Plugins bring agents, skills, hooks and MCP servers; what belongs to the project is written here:

    rules        — AIKit block in CLAUDE.md (Claude Code) or AGENTS.md (Codex): base + profile rules;
                   text outside the block stays as the team wrote it
    contracts    — .aikit/profiles.json: agents by role and commands of each profile
    memory       — .aikit/memory/ and the PRODUCT.md template, if the project has none
    settings     — .aikit/settings.json: team settings, such as asking for the commit message or committing by the rules
    claude       — .claude/settings.json: kit permissions and attribution, the aikit marketplace
                   and the enabled plugins, so teammates get the same set after trusting the folder
    codex        — .codex/agents/*.toml: Codex plugins cannot ship agents, so they are written here

The script runs from the core plugin (its root is the AIKit repository) via the /aikit:setup skill.
State of the previous run is kept in .aikit/plugin-init.json: agents it wrote and are no longer needed are removed.

Usage:
    python3 scripts/plugin-init.py --runtime claude --profiles vue-nuxt [--packs devops] [--commit ask|auto] [--workspace .]
    python3 scripts/plugin-init.py --runtime codex --preset frontend-team
    python3 scripts/plugin-init.py --runtime codex --refresh-agents    # only .codex/agents/*.toml, set of the previous run
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

import agent_models
import codex_content
import memory_paths
import preset_utils
import profile_contract
import project_settings
import rules
import runtime_settings

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE_NAME = "aikit"
CORE_PLUGIN = "aikit"
MARKETPLACE_REPO = "undef1ned-dev/ai-kit"
STATE_FILE = Path(".aikit") / "plugin-init.json"
LEGACY_ATTACH_MARKER = Path(".claude") / ".config-version"
RUNTIMES = ("claude", "codex", "antigravity")
RULES_FILES = rules.RULES_FILES


def load_script(file_name: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "scripts" / file_name)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Не удалось загрузить scripts/{file_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


installer = load_script("install-adapter-package.py", "aikit_install_adapter_package")
antigravity_installer = load_script("install-antigravity-plugins.py", "aikit_install_antigravity_plugins")


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise SystemExit(f"{path} не разобран как JSON — поправь файл и запусти снова")
    return data if isinstance(data, dict) else {}


def merge_runtimes(state: dict, runtime: str) -> list[str]:
    """Runtimes the project was set up for: the file is shared, so a rerun in one runtime must not drop the other."""
    known = state.get("runtimes")
    if not isinstance(known, list):
        known = [state.get("runtime")]
    merged = {name for name in known if name in RUNTIMES} | {runtime}
    return [name for name in RUNTIMES if name in merged]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def resolve_selection(args: argparse.Namespace) -> tuple[list[str], list[str]]:
    if args.preset:
        preset = preset_utils.resolve_preset(args.preset)
        profiles, packs = preset["profiles"], preset["packs"]
    else:
        profiles = [item for item in (args.profiles or "").split("+") if item]
        packs = []
    packs = list(dict.fromkeys([*packs, *(args.packs or "").split()]))
    if not profiles:
        raise SystemExit("Укажи --profiles a+b или --preset <имя>")
    for name in profiles:
        if not (ROOT / "profiles" / name / "profile.manifest.json").exists():
            raise SystemExit(f"Нет профиля '{name}'")
    for name in packs:
        if not (ROOT / "packs" / name / "pack.json").exists():
            raise SystemExit(f"Нет пака '{name}'")
    return profiles, packs


def render_rules_block(runtime: str, profiles: list[str]) -> str:
    return rules.render_block(runtime, profiles)


def merge_rules(workspace: Path, runtime: str, profiles: list[str]) -> str:
    path = workspace / RULES_FILES[runtime]
    block = render_rules_block(runtime, profiles)
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    pattern = re.compile(rf"{re.escape(installer.AGENTS_MD_BEGIN)}.*?{re.escape(installer.AGENTS_MD_END)}\n?", re.DOTALL)
    if pattern.search(original):
        updated = pattern.sub(lambda _: block, original)
    elif original.strip():
        updated = original.rstrip() + "\n\n" + block
    else:
        updated = block
    path.write_text(updated, encoding="utf-8", newline="\n")
    return path.name


def ensure_memory(workspace: Path) -> None:
    memory_paths.ensure_memory_structure(workspace / ".aikit" / "memory", ROOT / "base" / "memory" / "INDEX.md")
    product = workspace / "PRODUCT.md"
    if not product.exists():
        shutil.copyfile(ROOT / "base" / "PRODUCT.md", product)


def kit_settings(profiles: list[str], packs: list[str]) -> dict:
    sources = [ROOT / "base", *(ROOT / "profiles" / name for name in profiles), *(ROOT / "packs" / name for name in packs)]
    builder = installer.load_builder_module()
    return builder.merge_settings_documents([source / "settings.json" for source in sources])


def merge_claude_settings(workspace: Path, profiles: list[str], packs: list[str]) -> list[str]:
    """Kit permissions are added to the team's, kit keys (attribution) win; plugins are enabled for the project."""
    path = workspace / ".claude" / "settings.json"
    current = read_json(path)
    kit = kit_settings(profiles, packs)
    merged = current | {key: value for key, value in kit.items() if key != "permissions"}
    permissions = current.get("permissions") if isinstance(current.get("permissions"), dict) else {}
    for key in ("allow", "deny"):
        items = [*permissions.get(key, []), *kit.get("permissions", {}).get(key, [])]
        permissions[key] = list(dict.fromkeys(item for item in items if isinstance(item, str)))
    merged["permissions"] = permissions

    marketplaces = merged.get("extraKnownMarketplaces") if isinstance(merged.get("extraKnownMarketplaces"), dict) else {}
    marketplaces[MARKETPLACE_NAME] = {"source": {"source": "github", "repo": MARKETPLACE_REPO}}
    merged["extraKnownMarketplaces"] = marketplaces
    plugins = [CORE_PLUGIN, *profiles, *packs]
    enabled = merged.get("enabledPlugins") if isinstance(merged.get("enabledPlugins"), dict) else {}
    for name in plugins:
        enabled[f"{name}@{MARKETPLACE_NAME}"] = True
    merged["enabledPlugins"] = enabled
    write_json(path, merged)
    return plugins


def ensure_update_script(workspace: Path) -> Path:
    source = ROOT / "scripts" / "update-agents.sh"
    target = workspace / ".aikit" / "scripts" / "update-agents.sh"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8"))
    try:
        target.chmod(0o755)
    except OSError:
        pass
    return target


def write_codex_agents(workspace: Path, profiles: list[str], packs: list[str], previous: list[str]) -> list[str]:
    agents_dir = workspace / ".codex" / "agents"
    sources = codex_content.layers(profiles, packs)
    available = codex_content.agents(sources)
    codex_content.catalog(sources)
    for name in set(previous) - available.keys():
        (agents_dir / f"{name}.toml").unlink(missing_ok=True)
    rendered = codex_content.install_agents(sources, agents_dir)
    codex_content.write_catalog(sources, workspace / ".aikit/agent-catalog.json")
    agent_models.apply("codex", workspace)
    return rendered


def refresh_agents(workspace: Path, runtime: str = "codex") -> int:
    """Rewrite .codex/agents/ or .agents/agents/ from the kit with the profiles and packs of the previous run; nothing else is touched."""
    state_path = workspace / STATE_FILE
    state = read_json(state_path)
    if runtime not in merge_runtimes(state, "") or not state.get("profiles"):
        label = "Antigravity" if runtime == "antigravity" else "Codex"
        cmd = "/setup" if runtime == "antigravity" else "$aikit:setup"
        print(f"Проект не подключён к AIKit в {label}: сначала запусти {cmd}", file=sys.stderr)
        return 1
    profiles = [name for name in state["profiles"] if (ROOT / "profiles" / name / "profile.manifest.json").exists()]
    packs = [name for name in state.get("packs", []) if (ROOT / "packs" / name / "pack.json").exists()]
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if runtime == "antigravity":
        previous = state.get("antigravity_agents", []) if isinstance(state.get("antigravity_agents"), list) else []
        antigravity_agents = antigravity_installer.install_workspace_agents(workspace, profiles, packs, previous)
        ensure_update_script(workspace)
        write_json(state_path, {**state, "antigravity_agents": antigravity_agents, "antigravity_agents_version": version})
        print(f"Агенты Antigravity: .agents/agents/ ({len(antigravity_agents)} шт), профили {', '.join(profiles)}")
        return 0
    previous = state.get("codex_agents", []) if isinstance(state.get("codex_agents"), list) else []
    codex_agents = write_codex_agents(workspace, profiles, packs, previous)
    ensure_update_script(workspace)
    write_json(state_path, {**state, "codex_agents": codex_agents, "codex_agents_version": version})
    print(f"Агенты Codex: .codex/agents/ ({len(codex_agents)} шт), профили {', '.join(profiles)}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Connect a project to AIKit installed as plugins")
    parser.add_argument("--runtime", choices=RUNTIMES, required=True)
    parser.add_argument("--profiles", help="profile1+profile2")
    parser.add_argument("--preset", help="preset name from presets/")
    parser.add_argument("--packs", default="", help='extra packs: "devops"')
    parser.add_argument("--commit", choices=project_settings.COMMIT_MODES, help="ask for the commit message or commit by the rules")
    parser.add_argument("--refresh-agents", action="store_true", help="only rewrite .codex/agents/ for the set of the previous run")
    parser.add_argument("--workspace", default=".")
    return parser.parse_args()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    if args.refresh_agents:
        if args.runtime not in {"codex", "antigravity"}:
            raise SystemExit("--refresh-agents нужен только Codex и Antigravity: агенты Claude Code приходят из плагинов")
        return refresh_agents(workspace, args.runtime)
    profiles, packs = resolve_selection(args)
    state_path = workspace / STATE_FILE
    state = read_json(state_path)

    print(f"Правила: {merge_rules(workspace, args.runtime, profiles)}")
    print(f"Контракты профилей: {', '.join(profile_contract.install(workspace, profiles))}")
    ensure_memory(workspace)
    print("Память: .aikit/memory/, PRODUCT.md")
    print(f"Коммиты: {project_settings.describe(project_settings.write(workspace, args.commit))}")
    codex_agents = state.get("codex_agents", []) if isinstance(state.get("codex_agents"), list) else []
    antigravity_agents = state.get("antigravity_agents", []) if isinstance(state.get("antigravity_agents"), list) else []
    if args.runtime == "claude":
        plugins = merge_claude_settings(workspace, profiles, packs)
        print(f".claude/settings.json: права кита, плагины {', '.join(f'{name}@{MARKETPLACE_NAME}' for name in plugins)}")
    elif args.runtime == "codex":
        runtime_settings.install_codex(workspace)
        codex_agents = write_codex_agents(workspace, profiles, packs, codex_agents)
        ensure_update_script(workspace)
        print(f"Агенты Codex: .codex/agents/ ({len(codex_agents)} шт), .aikit/scripts/update-agents.sh")
    elif args.runtime == "antigravity":
        antigravity_agents = antigravity_installer.install_workspace_agents(workspace, profiles, packs, antigravity_agents)
        ensure_update_script(workspace)
        print(f"Агенты Antigravity: .agents/agents/ ({len(antigravity_agents)} шт), .aikit/scripts/update-agents.sh")
    next_state = {
        **state,
        "runtimes": merge_runtimes(state, args.runtime),
        "profiles": profiles,
        "packs": packs,
        "codex_agents": codex_agents,
    }
    if antigravity_agents or args.runtime == "antigravity":
        next_state["antigravity_agents"] = antigravity_agents
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if args.runtime == "codex":
        next_state["codex_agents_version"] = version
    elif args.runtime == "antigravity":
        next_state["antigravity_agents_version"] = version
    write_json(state_path, next_state)
    if (workspace / LEGACY_ATTACH_MARKER).exists():
        print(
            "! Проект раньше подключали через attach.sh: агенты и скиллы в .claude/ дублируют плагины. "
            "Удали .claude/agents/, .claude/skills/ кита и хуки aikit_hook.py из .claude/settings.json",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
