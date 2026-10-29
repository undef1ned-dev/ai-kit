#!/usr/bin/env python3
"""Inspect Codex configuration and hook run history without changing the project."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib

sys.dont_write_bytecode = True
import agent_models

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 10
HISTORY_AGE = dt.timedelta(days=1)
EVENTS = {"SessionStart", "PreToolUse", "PostToolUse", "Stop"}


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value


def read_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def cli_json(codex: str, args: list[str], workspace: Path):
    result = subprocess.run([codex, *args], cwd=workspace, capture_output=True, encoding="utf-8", errors="replace", timeout=TIMEOUT)
    if result.returncode:
        raise ValueError("CLI query failed")
    return json.loads(result.stdout)


def hook_python() -> dict:
    program = "python" if os.name == "nt" else "python3"
    executable = shutil.which(program)
    if not executable:
        return {"status": "error", "message": f"Команда хука {program} не найдена", "action": "Настрой PATH для Python 3.9+; запуск диагностики другим Python не исправляет окружение хука"}
    if "windowsapps" in executable.lower():
        return {"status": "unknown", "message": f"{program} разрешается в WindowsApps; это может быть лаунчер или заглушка", "action": "Проверь реальный Python для хука и отметки запусков; диагностика не запускает менеджер установки"}
    code = 'import json,sys;print(json.dumps(list(sys.version_info[:3])))'
    try:
        result = subprocess.run([executable, "-c", code], capture_output=True, encoding="utf-8", timeout=TIMEOUT)
        version = json.loads(result.stdout)
        if result.returncode or not isinstance(version, list) or len(version) != 3 or not all(isinstance(part, int) for part in version):
            raise ValueError("invalid Python response")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {"status": "error", "message": f"Команда хука {program} не прошла проверку запуска", "action": "Настрой рабочий Python 3.9+ в PATH"}
    if tuple(version) < (3, 9):
        return {"status": "warning", "message": f"Команда хука {program}: {'.'.join(map(str, version))}", "action": "Лаунчер Windows может передать событие новому Python; без отметки запуска это не подтверждено. Настрой Python 3.9+ в PATH"}
    return {"status": "ok", "message": f"Команда хука {program}: {'.'.join(map(str, version))}; это проверка shell, не запуска хука"}


def hook_history(workspace: Path, now: dt.datetime) -> dict:
    folder = Path(tempfile.gettempdir()) / "aikit-hooks"
    key = hashlib.sha1(str(workspace).encode("utf-8")).hexdigest()[:16]
    mark = read_json(folder / f"run-{key}.json")
    if not mark:
        hint = " Есть общая отметка ошибки лаунчера, которая может относиться к другому проекту." if (folder / "launch-error.txt").exists() else ""
        return {"status": "unknown", "message": "Нет отметки запуска для этого проекта." + hint, "action": "Открой новую сессию, проверь /hooks и повтори диагностику"}
    runtimes = mark.get("runtimes", {})
    codex_mark = runtimes.get("codex") if isinstance(runtimes, dict) else None
    if not isinstance(codex_mark, dict) or not codex_mark:
        return {"status": "unknown", "message": "Нет отдельной отметки Codex: старый формат или запускался только другой runtime", "action": "Обнови хуки и повтори диагностику после новой сессии Codex"}
    if codex_mark.get("last_error"):
        return {"status": "error", "message": "В последнем запуске хука Codex записана внутренняя ошибка", "action": "Проверь локальный aikit_hook.py --status; диагностика не выводит текст ошибки или данные событий"}
    events = codex_mark.get("events", {})
    stamps = [dt.datetime.fromisoformat(value) for key, value in events.items() if key in EVENTS and isinstance(value, str)] if isinstance(events, dict) else []
    if not stamps or any(stamp.tzinfo is None or stamp > now + dt.timedelta(minutes=5) for stamp in stamps):
        return {"status": "unknown", "message": "Отметка запуска не содержит корректного времени событий"}
    if now - max(stamps) > HISTORY_AGE:
        return {"status": "warning", "message": "Отметка Codex старше суток; текущая работа хуков не подтверждена", "action": "Повтори диагностику после новой сессии"}
    observed = sorted(key for key in events if key in EVENTS)
    return {"status": "ok", "message": "Недавние запуски Codex: " + ", ".join(observed), "observed_events": observed, "action": "Это история запусков, а не подтверждение одобрения текущей версии хуков"}


def diagnose(workspace: Path, *, codex_home: Path | None = None, now: dt.datetime | None = None) -> dict:
    checks = []
    now = now or dt.datetime.now(dt.timezone.utc)
    codex_home = codex_home or Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    def add(name: str, status: str, message: str, action: str = "", **details):
        checks.append({"id": name, "status": status, "message": message, **({"action": action} if action else {}), **details})
    def inspect(name, callback):
        try:
            return callback()
        except (OSError, ValueError, TypeError, AttributeError, subprocess.TimeoutExpired):
            add(name, "error", "Не удалось прочитать или разобрать данные проверки; содержимое не выводится", "Проверь формат соответствующего файла или доступность CLI")
            return None

    add("python.doctor", "ok", f"Диагностика запущена на Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    probe = inspect("python.hooks", hook_python)
    if probe:
        checks.append({"id": "python.hooks", **probe})
    state = inspect("project.state", lambda: read_json(workspace / ".aikit/plugin-init.json"))
    package = inspect("project.package", lambda: read_json(workspace / ".aikit/package.manifest.json"))
    contracts = inspect("project.contracts", lambda: read_json(workspace / ".aikit/profiles.json"))
    state, package, contracts = state or {}, package or {}, contracts or {}
    def selection(key):
        value = state.get(key, [])
        if not isinstance(value, list) or any(not isinstance(item, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", item) for item in value):
            add(f"project.{key}", "error", f"Некорректный список {key} в состоянии проекта")
            return []
        return value
    profiles, packs, owned_agents = selection("profiles"), selection("packs"), selection("codex_agents")
    repository = (workspace / "scripts/build-plugins.py").is_file() and (workspace / "base/RULES.md").is_file()
    runtimes = state.get("runtimes", [state.get("runtime")])
    plugin_mode = isinstance(runtimes, list) and "codex" in runtimes
    mode = "repository" if repository else "plugin" if plugin_mode else "adapter" if package.get("adapter_runtime") == "codex" else "unconnected"
    add("project", "error" if mode == "unconnected" else "ok", f"Режим: {mode}", "Подключи проект через setup или адаптер" if mode == "unconnected" else "")
    if mode in {"plugin", "adapter"} and not contracts.get("profiles"):
        add("contracts", "error", "Нет контрактов профилей", "Повтори setup или установку адаптера")
    project_rules = workspace / "AGENTS.md"
    if not project_rules.is_file():
        add("rules", "error", "Нет AGENTS.md", "Повтори setup или установку адаптера")
    else:
        add("rules", "ok", "AGENTS.md существует; применение в активной сессии отдельно не проверяется")

    config = inspect("trust.config", lambda: read_toml(codex_home / "config.toml"))
    trust = None
    projects = (config or {}).get("projects", {})
    if not isinstance(projects, dict):
        add("trust.config", "error", "Секция projects имеет неверный формат")
        projects = {}
    for path, value in projects.items():
        if Path(path).is_absolute() and os.path.normcase(os.path.abspath(path)) == os.path.normcase(str(workspace)) and isinstance(value, dict):
            trust = value.get("trust_level")
    add("trust", "ok" if trust == "trusted" else "error" if trust == "untrusted" else "unknown", "Доверие настроено в пользовательском config.toml" if trust == "trusted" else "Проект помечен недоверенным" if trust == "untrusted" else "Доверие к этому пути не подтверждено пользовательским config.toml", "Проверь доверие в новой сессии; управляемая политика и состояние активной сессии здесь не проверяются")

    def check_permissions():
        project_config = read_toml(workspace / ".codex/config.toml")
        user_config = config or {}
        template = read_toml(workspace / ".codex/aikit-permissions.example.toml")
        has_template = isinstance(template.get("permissions", {}).get("aikit"), dict)
        add("permissions.template", "ok" if has_template else "unknown", "Opt-in шаблон permissions.aikit присутствует; Codex его автоматически не загружает" if has_template else "Opt-in шаблон permissions.aikit не найден", "Повтори setup или обновление адаптера, если нужен отдельный шаблон; активный config автоматически не меняется" if not has_template else "")
        project_profiles = project_config.get("permissions", {})
        user_profiles = user_config.get("permissions", {})
        profile = project_profiles.get("aikit", user_profiles.get("aikit"))
        if not isinstance(profile, dict):
            add("permissions.definition", "unknown", "В прочитанных активных config нет определения permissions.aikit; отдельный шаблон не считается применённым", "При необходимости вручную проверь совместимость шаблона с версией Codex и политикой команды перед переносом в config; установка этого не делает")
        else:
            filesystem = profile.get("filesystem", {})
            rules = filesystem.get(":workspace_roots", {})
            expected = profile.get("extends") == ":workspace" and all(rules.get(pattern) == "deny" for pattern in ("**/.env", "**/.env.*"))
            add("permissions.definition", "ok" if expected else "warning", "Определение permissions.aikit присутствует; это не подтверждение применения" if expected else "permissions.aikit отличается от нативного профиля AIKit", "Проверь профиль вручную; пользовательское определение setup не перезаписывает" if not expected else "")
        selected = project_config.get("default_permissions", user_config.get("default_permissions"))
        legacy = any("sandbox_mode" in layer or "sandbox_workspace_write" in layer for layer in (user_config, project_config))
        if legacy:
            add("permissions.application", "warning", "В прочитанных файлах есть legacy sandbox settings; применение permissions.aikit не подтверждено", "Проверь активную конфигурацию Codex: legacy sandbox_mode перекрывает default_permissions. Не удаляй ограничения автоматически; согласуй переход и открой новую сессию")
        elif selected != "aikit":
            add("permissions.application", "unknown", "permissions.aikit не выбран в прочитанных файлах; защита чтения через этот профиль не подтверждена", 'Если нужен профиль AIKit, сначала проверь совместимость шаблона и перенеси определение вручную, затем явно выбери default_permissions="aikit". CLI, managed config и другие слои здесь не проверены')
        else:
            add("permissions.application", "unknown", "В файлах выбран permissions.aikit; эффективная политика и защита чтения в активной сессии не проверены", "Проверь активный профиль и ограничения Codex в новой сессии: CLI, managed config, профили и другие слои могут переопределить эти файлы. Наличие TOML не доказывает блокировку чтения")
    inspect("permissions.config", check_permissions)

    codex = shutil.which("codex")
    add("codex.cli", "ok" if codex else "unknown", "Codex CLI найден" if codex else "Codex CLI не найден; эффективные плагины и MCP не проверены")
    records = None
    selected = ["aikit", *profiles, *packs] if plugin_mode and not repository else ["aikit"] if repository else []
    if codex and selected:
        response = inspect("plugins.cli", lambda: cli_json(codex, ["plugin", "list", "--marketplace", "aikit", "--json"], workspace))
        if isinstance(response, dict) and isinstance(response.get("installed"), list):
            records = {item.get("name"): item for item in response["installed"] if isinstance(item, dict) and item.get("name") in selected and item.get("marketplaceName") == "aikit"}
            for name in selected:
                record = records.get(name, {})
                enabled = record.get("installed") is True and record.get("enabled") is True
                add(f"plugin.{name}", "ok" if enabled else "warning" if repository else "error", "Плагин установлен и включён" if enabled else "Плагин не установлен или выключен", "Установи и включи требуемый плагин" if not enabled else "")
        elif response is not None:
            add("plugins.cli", "unknown", "Неизвестный формат списка плагинов Codex")

    def check_agents():
        expected = {"aikit-maintainer"} if repository else set(owned_agents)
        if mode == "adapter":
            expected.update(path.stem for path in (workspace / ".aikit/agents").glob("*.toml"))
        for profile in contracts.get("profiles", {}).values():
            expected.update(profile.get("agents", {}).values())
            expected.update(item["agent"] for item in profile.get("specialists", {}).values())
            for pipeline in profile.get("pipelines", {}).values():
                expected.update(pipeline.get("steps", []))
        if not expected:
            add("agents", "unknown", "Нет списка ожидаемых агентов", "Проверь setup и .aikit/profiles.json")
            return
        model_plan = {path.stem: fields for path, fields in agent_models.plan("codex", workspace)}
        problems = []
        for name in sorted(expected):
            if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", name):
                problems.append("Некорректное имя агента в контракте или состоянии")
                continue
            path = workspace / ".codex/agents" / f"{name}.toml"
            if not path.is_file():
                problems.append(f"{name}: нет TOML")
                continue
            agent = read_toml(path)
            if agent.get("name") != name or not agent.get("description") or not agent.get("developer_instructions"):
                problems.append(f"{name}: неполное определение")
            if agent.get("model") in {"opus", "sonnet", "haiku"}:
                problems.append(f"{name}: вместо модели Codex записан алиас")
            if any(agent.get(key) != value for key, value in model_plan.get(name, {}).items()):
                problems.append(f"{name}: модель или effort расходится с настройками проекта")
        add("agents", "error" if problems else "ok", f"Проверено определений: {len(expected)}; загрузка в сессию не проверяется", "Пересобери агентов скиллом update-agents" if problems else "", problems=problems)
    inspect("agents", check_agents)

    source_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else package.get("repo_version")
    recorded = state.get("codex_agents_version") if plugin_mode else package.get("repo_version")
    active_version = records.get("aikit", {}).get("version") if records is not None else None
    if not repository:
        mismatch = bool(recorded and ((source_version and recorded != source_version) or (active_version and recorded != active_version)))
        add("agents.version", "warning" if mismatch else "ok" if recorded else "unknown", "Версии источника и агентов расходятся" if mismatch else "Версия пересборки записана; совпадение не доказывает загрузку в текущую сессию" if recorded else "Версия пересборки не записана", "Используй update-agents --with-plugins и новую сессию" if mismatch else "")

    hook_config = inspect("hooks.file", lambda: read_json(workspace / ".codex/hooks.json")) or {}
    plugin_config = {}
    if records and records.get("aikit", {}).get("enabled") is True:
        source = records["aikit"].get("source", {})
        if isinstance(source, dict) and source.get("source") == "local" and isinstance(source.get("path"), str) and Path(source["path"]).is_absolute():
            plugin_config = inspect("hooks.plugin", lambda: read_json(Path(source["path"]) / ".codex-plugin/plugin.json")) or {}
        else:
            add("hooks.plugin", "unknown", "CLI не сообщил проверяемый локальный источник хуков плагина")
    def configured_events(config):
        hooks = config.get("hooks", {})
        if not isinstance(hooks, dict):
            return set()
        return {event for event, groups in hooks.items() if isinstance(groups, list) and any(isinstance(group, dict) and any(isinstance(handler, dict) and "aikit_hook.py" in str(handler.get("command", "")) for handler in group.get("hooks", [])) for group in groups)}
    events = configured_events(hook_config)
    if records and records.get("aikit", {}).get("enabled") is True:
        plugin_hooks = plugin_config.get("hooks", {})
        if isinstance(plugin_hooks, dict):
            events.update(configured_events(plugin_hooks))
    missing_events = sorted(EVENTS - events)
    add("hooks.config", "warning" if missing_events else "ok", "Не найдены конфигурации событий AIKit" if missing_events else "Конфигурации четырёх событий присутствуют", "Проверь setup или конфигурацию плагина" if missing_events else "", missing_events=missing_events)
    add("hooks.approval", "unknown", "Одобрение текущей версии хуков автоматически не подтверждается", "Проверь /hooks в Codex после установки и обновления")
    history = inspect("hooks.history", lambda: hook_history(workspace, now))
    if history:
        checks.append({"id": "hooks.history", **history})

    def check_mcp():
        expected = {}
        for folder in [ROOT / "base", *(ROOT / "profiles" / name for name in profiles), *(ROOT / "packs" / name for name in packs)]:
            expected.update(read_json(folder / "mcp.json").get("servers", {}))
        if mode == "adapter":
            expected.update({name: {} for name in read_json(workspace / ".aikit/mcp-servers.json").get("codex", [])})
        configured = read_toml(workspace / ".codex/config.toml").get("mcp_servers", {})
        listing = cli_json(codex, ["mcp", "list", "--json"], workspace) if codex else None
        if listing is not None and not isinstance(listing, list):
            add("mcp", "unknown", "Неизвестный формат списка MCP")
            return
        servers = {item.get("name"): item for item in listing or [] if isinstance(item, dict)}
        for name, requirements in expected.items():
            server = servers.get(name)
            local = configured.get(name, {})
            if server is None:
                add(f"mcp.{name}", "unknown" if local or not codex else "error", "MCP есть в файле, но применение не подтверждено" if local else "MCP не найден в эффективной конфигурации CLI", "Проверь установку, доверие проекту и новую сессию")
                continue
            if server.get("enabled") is not True:
                add(f"mcp.{name}", "error", "MCP выключен", "Включи сервер в настройках Codex")
                continue
            transport = server.get("transport", {})
            missing = [key for key in requirements.get("env_vars", []) if key not in os.environ and key not in (transport.get("env") or {})]
            auth = server.get("auth_status")
            add(f"mcp.{name}", "warning" if missing or auth == "not_logged_in" else "ok", "Конфигурация MCP найдена; соединение и вызовы инструментов не проверялись", "Выполни codex mcp login для этого сервера" if auth == "not_logged_in" else "Добавь требуемые переменные окружения" if missing else "", missing_env=missing)
        if not expected:
            add("mcp", "unknown", "Нет списка ожидаемых MCP-серверов")
    inspect("mcp", check_mcp)
    levels = {check["status"] for check in checks}
    status = next((level for level in ("error", "warning", "unknown") if level in levels), "ok")
    return {"runtime": "codex", "mode": mode, "status": status, "scope": "Конфигурация и история запусков; доступ к модели, текущая сессия и соединения MCP не проверяются", "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--json", action="store_true", help="machine-readable, sanitized report")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        report = diagnose(Path(args.workspace).resolve())
    except (OSError, ValueError, TypeError, AttributeError):
        report = {"runtime": "codex", "status": "error", "scope": "Конфигурация", "checks": [{"id": "configuration", "status": "error", "message": "Некорректная конфигурация: диагностика не завершена. Значения конфигурации не выводятся"}]}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(report["scope"])
        for check in report["checks"]:
            print(f"[{check['status']}] {check['id']}: {check['message']}")
            for problem in check.get("problems", []):
                print(f"  {problem}")
            if check.get("action"):
                print(f"  {check['action']}")
    return 1 if report["status"] == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
