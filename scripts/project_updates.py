"""Release journal for project files managed by AIKit plugins."""

from __future__ import annotations

import json
import re
from pathlib import Path

from release_utils import is_semver, version_tuple

JOURNAL = Path("scripts/project-updates.json")
PENDING = "Unreleased"
RUNTIMES = ("claude", "codex", "antigravity")
ACTIONS = {
    "rules": "Обновить управляемый блок правил проекта.",
    "contracts": "Синхронизировать контракты профилей с сохранением команд, действий и корней команды.",
    "claude-settings": "Добавить настройки и разрешения AIKit в проектный конфиг Claude Code.",
    "codex-plugins": "Включить выбранные плагины в проектном конфиге Codex.",
    "codex-permissions": "Обновить шаблон разрешений Codex.",
    "codex-agents": "Пересобрать агенты Codex и каталог с учётом моделей команды.",
    "antigravity-agents": "Пересобрать агенты Antigravity с учётом моделей команды.",
}
ACTION_RUNTIMES = {
    "claude-settings": "claude",
    "codex-plugins": "codex",
    "codex-permissions": "codex",
    "codex-agents": "codex",
    "antigravity-agents": "antigravity",
}
NAME = re.compile(r"[a-z][a-z0-9-]*")


def read(root: Path) -> dict:
    path = root / JOURNAL
    journal = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(journal, dict):
        raise ValueError("Журнал обновлений должен быть объектом JSON")
    for version, entries in journal.items():
        if (version != PENDING and not is_semver(version)) or not isinstance(entries, list):
            raise ValueError(f"Некорректная секция журнала: {version}")
        for entry in entries:
            if not isinstance(entry, dict) or entry.keys() - {"action", "runtime", "profile", "pack", "note"}:
                raise ValueError(f"Некорректная запись журнала: {version}")
            action, runtime = entry.get("action"), entry.get("runtime")
            if not isinstance(action, str) or action not in ACTIONS or ("runtime" in entry and runtime not in RUNTIMES):
                raise ValueError(f"Неизвестное действие или runtime в журнале: {version}")
            if action in ACTION_RUNTIMES and runtime not in (None, ACTION_RUNTIMES[action]):
                raise ValueError(f"Действие {action} несовместимо с runtime {runtime}")
            for field in ("profile", "pack"):
                if field in entry and (not isinstance(entry[field], str) or not NAME.fullmatch(entry[field])):
                    raise ValueError(f"Некорректный фильтр {field} в журнале: {version}")
            if "note" in entry and (not isinstance(entry["note"], str) or not entry["note"].strip()):
                raise ValueError(f"Некорректное описание в журнале: {version}")
    return journal


def infer(paths: list[str]) -> list[dict]:
    changes = []
    for path in paths:
        parts = path.split("/")
        if path in ("base/RULES.md", "scripts/rules.py"):
            changes.append({"action": "rules"})
        elif path == "base/settings.json":
            changes.append({"action": "claude-settings"})
        elif path == "scripts/runtime_settings.py":
            changes.extend([{"action": "codex-plugins"}, {"action": "codex-permissions"}])
        elif path == "base/codex/settings.toml":
            changes.append({"action": "codex-permissions"})
        elif path == "scripts/profile_contract.py":
            changes.append({"action": "contracts"})
        elif path in ("adapters/models.json", "scripts/agent_models.py", "scripts/update-agents.sh"):
            changes.extend([{"action": "codex-agents"}, {"action": "antigravity-agents"}])
        elif path == "scripts/codex_content.py":
            changes.append({"action": "codex-agents"})
        elif path == "scripts/install-antigravity-plugins.py" or (parts[0] == "base" and markdown_agent(parts[1:])):
            changes.append({"action": "antigravity-agents"})
        elif parts[:2] == ["base", "codex"] and agent_source(parts[2:]):
            changes.append({"action": "codex-agents"})
        elif len(parts) == 3 and parts[0] == "adapters" and parts[1] in RUNTIMES and parts[2] == "rules.md":
            changes.append({"action": "rules", "runtime": parts[1]})
        elif len(parts) >= 3 and parts[0] in ("profiles", "packs"):
            layer, name, *rest = parts
            scope = {"profile" if layer == "profiles" else "pack": name}
            if rest == ["RULES.md"] and layer == "profiles":
                changes.append({"action": "rules", **scope})
            elif rest == ["profile.manifest.json"] and layer == "profiles":
                changes.append({"action": "contracts", **scope})
            elif rest == ["settings.json"]:
                changes.append({"action": "claude-settings", **scope})
            elif rest[0] == "codex" and agent_source(rest[1:]):
                changes.append({"action": "codex-agents", **scope})
            elif markdown_agent(rest):
                changes.append({"action": "antigravity-agents", **scope})
    return changes


def agent_source(parts: list[str]) -> bool:
    return parts == ["catalog.json"] or (len(parts) == 2 and parts[0] == "agents" and parts[1].endswith(".toml"))


def markdown_agent(parts: list[str]) -> bool:
    return len(parts) == 2 and parts[0] == "agents" and parts[1].endswith(".md")


def release(root: Path, version: str, paths: list[str]) -> None:
    journal = read(root)
    released = journal.pop(PENDING, [])
    for entry in infer(paths):
        if all(entry != {key: value for key, value in known.items() if key != "note"} for known in released):
            released.append(entry)
    if released:
        journal[version] = released
    data = {PENDING: [], **journal}
    (root / JOURNAL).write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def select(journal: dict, current: str, target: str, runtime: str, profiles: list[str], packs: list[str]) -> list[tuple[str, dict]]:
    lower, upper = version_tuple(current), version_tuple(target)
    versions = sorted((version for version in journal if version != PENDING), key=version_tuple)
    return [
        (version, entry)
        for version in versions if lower < version_tuple(version) <= upper
        for entry in journal[version]
        if entry.get("runtime", runtime) == runtime
        and ACTION_RUNTIMES.get(entry["action"], runtime) == runtime
        and ("profile" not in entry or entry["profile"] in profiles)
        and ("pack" not in entry or entry["pack"] in packs)
    ]
