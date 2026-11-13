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
    codex        — .codex/agents/*.toml and project plugin enablement in .codex/config.toml

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
import os
import re
import shutil
import stat
import sys
import tempfile
from pathlib import Path

import agent_models
import codex_content
import memory_paths
import preset_utils
import profile_contract
import project_settings
import project_updates
from release_utils import version_tuple
import rules
import runtime_settings
from update_files import atomic_write

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
    merged = {name for name in RUNTIMES if name in known} | {runtime}
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
    original = path.read_bytes().decode("utf-8") if path.exists() else ""
    pattern = re.compile(rf"{re.escape(installer.AGENTS_MD_BEGIN)}.*?{re.escape(installer.AGENTS_MD_END)}(?:\r?\n)?", re.DOTALL)
    if pattern.search(original):
        updated = pattern.sub(lambda _: block, original)
    elif original.strip():
        separator = "" if original.endswith(("\n\n", "\r\n\r\n")) else "\n" if original.endswith("\n") else "\n\n"
        updated = original + separator + block
    else:
        updated = block
    path.write_bytes(updated.encode("utf-8"))
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


def merge_claude_settings(workspace: Path, profiles: list[str], packs: list[str], *, updating: bool = False) -> list[str]:
    """Kit permissions are added to the team's, kit keys (attribution) win; plugins are enabled for the project."""
    path = workspace / ".claude" / "settings.json"
    current = read_json(path)
    kit = kit_settings(profiles, packs)
    defaults = {key: value for key, value in kit.items() if key != "permissions"}
    merged = defaults | current if updating else current | defaults
    permissions = current.get("permissions") if isinstance(current.get("permissions"), dict) else {}
    for key in ("allow", "deny"):
        items = [*permissions.get(key, []), *kit.get("permissions", {}).get(key, [])]
        permissions[key] = list(dict.fromkeys(item for item in items if isinstance(item, str)))
    merged["permissions"] = permissions

    marketplaces = merged.get("extraKnownMarketplaces") if isinstance(merged.get("extraKnownMarketplaces"), dict) else {}
    marketplace = {"source": {"source": "github", "repo": MARKETPLACE_REPO}}
    if updating:
        marketplaces.setdefault(MARKETPLACE_NAME, marketplace)
    else:
        marketplaces[MARKETPLACE_NAME] = marketplace
    merged["extraKnownMarketplaces"] = marketplaces
    plugins = [CORE_PLUGIN, *profiles, *packs]
    enabled = merged.get("enabledPlugins") if isinstance(merged.get("enabledPlugins"), dict) else {}
    for name in plugins:
        plugin_id = f"{name}@{MARKETPLACE_NAME}"
        if updating:
            enabled.setdefault(plugin_id, True)
        else:
            enabled[plugin_id] = True
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


def saved_names(state: dict, key: str) -> list[str]:
    names = state.get(key, [])
    if not isinstance(names, list) or any(not isinstance(name, str) or not codex_content.NAME.fullmatch(name) for name in names):
        raise ValueError(f"Некорректный список {key} в {STATE_FILE}")
    return names


def enable_codex_plugins(workspace: Path, profiles: list[str], packs: list[str]) -> None:
    runtime_settings.install_codex_plugins(workspace, [f"{name}@{MARKETPLACE_NAME}" for name in [CORE_PLUGIN, *profiles, *packs]])


def owns_shared_rules(workspace: Path, runtime: str, state: dict) -> bool:
    if not {"codex", "antigravity"} <= set(merge_runtimes(state, "")) or runtime == "claude":
        return True
    other = "antigravity" if runtime == "codex" else "codex"
    path = workspace / RULES_FILES[runtime]
    if not path.is_file():
        return True
    block = path.read_text(encoding="utf-8").partition(rules.BEGIN)[2].partition(rules.END)[0]
    heading = (ROOT / "adapters" / other / "rules.md").read_text(encoding="utf-8").splitlines()[0]
    return heading not in block.splitlines()


def snapshot(path: Path) -> tuple[bytes, int] | None:
    if any(item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()) for item in (path, *path.parents)):
        raise ValueError(f"Обновление не записывает файлы через символические ссылки: {path}")
    return (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) if path.exists() else None


def promote_project_update(workspace: Path, stage: Path, before: dict, paths: list[Path]) -> None:
    after = {path: snapshot(stage / path) for path in paths}
    if any(snapshot(workspace / path) != data for path, data in before.items()):
        raise ValueError("Файлы проекта изменились во время подготовки обновления. Повтори команду.")

    def write(relative: Path, data: tuple[bytes, int] | None) -> None:
        path = workspace / relative
        if data is None:
            path.unlink(missing_ok=True)
        else:
            content, mode = data
            atomic_write(path, content)
            os.chmod(path, mode)

    written = []
    try:
        for path, data in after.items():
            if data != before[path]:
                written.append(path)
                write(path, data)
                print(f"  {'Удалён' if data is None else 'Обновлён' if before[path] is not None else 'Добавлен'}: {path.as_posix()}")
    except (Exception, KeyboardInterrupt):
        for path in reversed(written):
            if snapshot(workspace / path) != before[path]:
                write(path, before[path])
        raise


def update_project(workspace: Path, runtime: str, *, preview: bool) -> None:
    state_path = workspace / STATE_FILE
    state = read_json(state_path)
    if runtime not in merge_runtimes(state, ""):
        raise ValueError(f"В {STATE_FILE} нет установки AIKit для {runtime}. Для установки адаптером используй его обновление.")
    profiles, packs = saved_names(state, "profiles"), saved_names(state, "packs")
    if not profiles:
        raise ValueError(f"В {STATE_FILE} нет профилей проекта")
    versions = state.get("project_versions", {})
    if not isinstance(versions, dict):
        raise ValueError(f"Некорректные project_versions в {STATE_FILE}")
    current = versions.get(runtime, "0.0.0")
    if not isinstance(current, str):
        raise ValueError(f"Некорректная версия {runtime} в {STATE_FILE}")
    target = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if version_tuple(current) > version_tuple(target):
        raise ValueError(f"Проект уже обновлён до {current}. Открой сессию с актуальным плагином AIKit.")
    journal = project_updates.read(ROOT)
    entries = project_updates.select(journal, current, target, runtime, profiles, packs)
    if any(entry["action"] == "rules" for _, entry in entries) and not owns_shared_rules(workspace, runtime, state):
        entries = [(version, entry) for version, entry in entries if entry["action"] != "rules"]
        print("Блок AIKit в AGENTS.md относится к другому runtime. Его обновляет команда из того runtime.")
    actions = {entry["action"] for _, entry in entries}
    print(f"{runtime}: {current if runtime in versions else 'версия проекта не записана'} → {target}")
    print(f"Профили: {', '.join(profiles)}. Паки: {', '.join(packs) or '—'}")
    for version, entry in entries:
        print(f"- {version}: {entry.get('note', project_updates.ACTIONS[entry['action']])}")
    if not entries:
        print("Для этого проекта нет миграций.")
    for name in profiles:
        if not (ROOT / "profiles" / name / "profile.manifest.json").is_file():
            raise ValueError(f"Профиль {name} отсутствует в источнике AIKit {target}")
    for name in packs:
        if not (ROOT / "packs" / name / "pack.json").is_file():
            raise ValueError(f"Пак {name} отсутствует в источнике AIKit {target}")
    if preview or current == target:
        return
    paths = []
    if "rules" in actions:
        paths.append(Path(RULES_FILES[runtime]))
    if "contracts" in actions:
        paths.extend([profile_contract.PROFILES_FILE, profile_contract.DEFAULTS_FILE])
    if "claude-settings" in actions:
        paths.append(Path(".claude/settings.json"))
    if actions & {"codex-plugins", "codex-permissions"}:
        paths.append(Path(".codex/config.toml"))
    if "codex-permissions" in actions:
        paths.append(runtime_settings.TARGET)
    refresh_local_agents = f"{runtime}-agents" in actions
    if refresh_local_agents:
        agents_key = f"{runtime}_agents"
        previous = saved_names(state, agents_key)
        agents_version_key = f"{agents_key}_version"
        if version_tuple(state.get(agents_version_key) or "0.0.0") > version_tuple(target):
            raise ValueError("Агенты собраны из более свежего плагина AIKit. Открой новую сессию.")
        if runtime == "codex":
            agents = codex_content.agents(codex_content.layers(profiles, packs))
            agent_dir, extension = Path(".codex/agents"), ".toml"
            paths.append(Path(".aikit/agent-catalog.json"))
            install_agents = write_codex_agents
        else:
            agents = antigravity_installer.workspace_agent_sources(profiles, packs)
            agent_dir, extension = Path(".agents/agents"), ".md"
            install_agents = antigravity_installer.install_workspace_agents
        paths.extend(agent_dir / f"{name}{extension}" for name in sorted(agents.keys() | set(previous)))
        paths.append(Path(".aikit/scripts/update-agents.sh"))
    paths.append(STATE_FILE)
    inputs = [*paths, agent_models.PROJECT_MODELS] if refresh_local_agents else paths
    before = {path: snapshot(workspace / path) for path in inputs}
    if before[STATE_FILE] is None or json.loads(before[STATE_FILE][0]) != state:
        raise ValueError("Состояние AIKit изменилось во время подготовки обновления. Повтори команду.")
    if refresh_local_agents:
        for name in sorted(agents.keys() - set(previous)):
            if before[agent_dir / f"{name}{extension}"] is not None:
                raise ValueError(f"Агент {name} уже существует и не принадлежит установке AIKit")
    with tempfile.TemporaryDirectory(prefix="aikit-project-update-") as folder:
        stage = Path(folder)
        for path, data in before.items():
            if data is not None:
                (stage / path).parent.mkdir(parents=True, exist_ok=True)
                (stage / path).write_bytes(data[0])
                (stage / path).chmod(data[1])
        if "rules" in actions:
            merge_rules(stage, runtime, profiles)
        if "contracts" in actions and profile_contract.read_json(stage / profile_contract.DEFAULTS_FILE) is None:
            raise ValueError(f"Исправь JSON в {profile_contract.DEFAULTS_FILE}")
        if "contracts" in actions and not profile_contract.install(stage, profiles, project_root=workspace):
            raise ValueError("Контракты профилей не обновлены")
        if "claude-settings" in actions:
            merge_claude_settings(stage, profiles, packs, updating=True)
        if "codex-plugins" in actions:
            enable_codex_plugins(stage, profiles, packs)
        if "codex-permissions" in actions:
            runtime_settings.install_codex(stage)
        next_state = {**state, "project_versions": {**versions, runtime: target}}
        if refresh_local_agents:
            next_state[agents_key] = install_agents(stage, profiles, packs, previous)
            next_state[agents_version_key] = target
            ensure_update_script(stage)
        write_json(stage / STATE_FILE, next_state)
        promote_project_update(workspace, stage, before, paths)
    print(f"Обновление проекта до {target} записано в {STATE_FILE}.")


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
    parser.add_argument("--update", action="store_true", help="apply project migrations from the installed plugin")
    parser.add_argument("--dry-run", action="store_true", help="show project migrations without writing")
    parser.add_argument("--workspace", default=".")
    return parser.parse_args()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    if args.update:
        if args.runtime not in project_updates.RUNTIMES or any((args.refresh_agents, args.profiles, args.preset, args.packs, args.commit)):
            raise SystemExit("--update берёт профили, паки и режим коммитов из проекта. Запусти его без аргументов установки или пересборки агентов.")
        try:
            update_project(workspace, args.runtime, preview=args.dry_run)
        except (OSError, ValueError, TypeError) as error:
            raise SystemExit(f"Обновление проекта не завершено: {error}") from error
        return 0
    if args.dry_run:
        raise SystemExit("--dry-run доступен вместе с --update")
    if args.refresh_agents:
        if args.runtime not in {"codex", "antigravity"}:
            raise SystemExit("--refresh-agents нужен только Codex и Antigravity: агенты Claude Code приходят из плагинов")
        return refresh_agents(workspace, args.runtime)
    profiles, packs = resolve_selection(args)
    state_path = workspace / STATE_FILE
    state = read_json(state_path)

    if args.runtime == "codex":
        enable_codex_plugins(workspace, profiles, packs)

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
        print(".codex/config.toml: плагины AIKit включены на уровне проекта; пользовательские настройки плагинов сохраняются")
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
    if args.runtime in project_updates.RUNTIMES:
        versions = state.get("project_versions", {})
        next_state["project_versions"] = {**(versions if isinstance(versions, dict) else {}), args.runtime: version}
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
