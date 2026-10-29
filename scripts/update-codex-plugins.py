#!/usr/bin/env python3
"""Refresh the AIKit marketplace and rebuild project agents from its updated source."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from release_utils import is_semver

MARKETPLACE = "aikit"
STATE_FILE = Path(".aikit/plugin-init.json")
AGENTS_DIR = Path(".codex/agents")
CATALOG_FILE = Path(".aikit/agent-catalog.json")
NAME = re.compile(r"^[a-z][a-z0-9-]*$")
COMMAND_TIMEOUT = 300


class UpdateError(Exception):
    pass


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise UpdateError(f"{path}: ожидался объект JSON")
    return value


def names(value, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not NAME.fullmatch(item) for item in value):
        raise UpdateError(f"Некорректный список {label}")
    return list(dict.fromkeys(value))


def command(argv: list[str], workspace: Path) -> str:
    try:
        result = subprocess.run(argv, cwd=workspace, capture_output=True, encoding="utf-8", errors="replace", timeout=COMMAND_TIMEOUT)
    except subprocess.TimeoutExpired as error:
        raise UpdateError(f"Превышено время команды: {' '.join(argv[:4])}") from error
    if result.returncode:
        raise UpdateError(f"Команда завершилась с кодом {result.returncode}: {' '.join(argv[:4])}\n{result.stderr[-2000:]}")
    return result.stdout


def installed_plugins(codex: str, workspace: Path, required: list[str]) -> dict[str, dict]:
    data = json.loads(command([codex, "plugin", "list", "--marketplace", MARKETPLACE, "--json"], workspace))
    if not isinstance(data, dict) or not isinstance(data.get("installed"), list):
        raise UpdateError("Codex CLI вернул неизвестный формат plugin list --json")
    found = {}
    for record in data["installed"]:
        if not isinstance(record, dict) or record.get("name") not in required or record.get("marketplaceName") != MARKETPLACE:
            continue
        if record.get("installed") is not True or record.get("enabled") is not True:
            raise UpdateError(f"Плагин {record.get('name')}@{MARKETPLACE} не установлен или выключен")
        if record["name"] in found:
            raise UpdateError(f"Несколько записей плагина {record['name']}@{MARKETPLACE}")
        if not isinstance(record.get("version"), str) or not is_semver(record["version"]):
            raise UpdateError(f"Нет версии плагина {record['name']}@{MARKETPLACE}")
        found[record["name"]] = record
    missing = set(required) - found.keys()
    if missing:
        raise UpdateError(f"Сначала установи и включи плагины: {', '.join(sorted(missing))}. Набор берётся из {STATE_FILE}")
    return found


def updated_source(records: dict[str, dict], profiles: list[str], packs: list[str]) -> Path:
    version = records["aikit"]["version"]
    roots = {}
    for name, record in records.items():
        source = record.get("source")
        if not isinstance(source, dict) or source.get("source") != "local" or not isinstance(source.get("path"), str):
            raise UpdateError(f"CLI не сообщил локальный источник {name}@{MARKETPLACE}")
        path = Path(source["path"])
        if not path.is_absolute():
            raise UpdateError(f"Источник {name}@{MARKETPLACE} должен быть абсолютным путём")
        manifest = read_json(path / ".codex-plugin/plugin.json")
        if record["version"] != version or manifest.get("version") != version or manifest.get("name") != name:
            raise UpdateError(f"Версии ядра и плагина {name} не совпадают; агенты не обновлены")
        roots[name] = path
    root = roots["aikit"]
    if (root / "VERSION").read_text(encoding="utf-8").strip() != version:
        raise UpdateError("VERSION источника ядра не совпадает с версией из Codex CLI")
    if not (root / "scripts/plugin-init.py").is_file():
        raise UpdateError("В обновлённом источнике ядра нет scripts/plugin-init.py")
    for kind, selected, manifest in (("profiles", profiles, "profile.manifest.json"), ("packs", packs, "pack.json")):
        for name in selected:
            if not (root / kind / name / manifest).is_file():
                raise UpdateError(f"В обновлённом ядре нет {kind}/{name}; сначала скорректируй setup")
    return root


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".aikit-update-", delete=False) as output:
        temporary = Path(output.name)
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def promote(workspace: Path, stage: Path, old_names: list[str], new_names: list[str], state: dict) -> None:
    changes = {AGENTS_DIR / f"{name}.toml": (stage / AGENTS_DIR / f"{name}.toml").read_bytes() for name in new_names}
    changes.update({AGENTS_DIR / f"{name}.toml": None for name in set(old_names) - set(new_names)})
    changes[CATALOG_FILE] = (stage / CATALOG_FILE).read_bytes()
    changes[STATE_FILE] = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    for name in set(new_names) - set(old_names):
        if (workspace / AGENTS_DIR / f"{name}.toml").exists():
            raise UpdateError(f"Агент {name} уже существует и не принадлежит прежней установке AIKit")
    backups = {relative: (workspace / relative).read_bytes() if (workspace / relative).exists() else None for relative in changes}
    written = []
    try:
        for relative, data in changes.items():
            path = workspace / relative
            if data is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, data)
            written.append(relative)
    except (Exception, KeyboardInterrupt):
        for relative in reversed(written):
            if backups[relative] is None:
                (workspace / relative).unlink(missing_ok=True)
            else:
                atomic_write(workspace / relative, backups[relative])
        raise


def update(workspace: Path, codex: str) -> dict:
    try:
        import tomllib
    except ImportError as error:
        raise UpdateError("Для проверки агентов нужен Python 3.11+") from error
    state = read_json(workspace / STATE_FILE)
    runtimes = state.get("runtimes", [state.get("runtime")])
    if not isinstance(runtimes, list) or "codex" not in runtimes:
        raise UpdateError("Проект не подключён к плагинам AIKit в Codex: сначала вызови setup")
    profiles = names(state.get("profiles"), "profiles")
    packs = names(state.get("packs", []), "packs")
    previous = names(state.get("codex_agents", []), "codex_agents")
    if not profiles:
        raise UpdateError("Нет подключённых профилей; сначала вызови setup")
    required = list(dict.fromkeys(["aikit", *profiles, *packs]))
    before = installed_plugins(codex, workspace, required)
    print("Обновление маркетплейса aikit (все установленные из него плагины)...", flush=True)
    command([codex, "plugin", "marketplace", "upgrade", MARKETPLACE, "--json"], workspace)
    after = installed_plugins(codex, workspace, required)
    for name in required:
        if tuple(map(int, after[name]["version"].split("."))) < tuple(map(int, before[name]["version"].split("."))):
            raise UpdateError(f"Версия {name} понизилась; агенты не обновлены")
    root = updated_source(after, profiles, packs)
    with tempfile.TemporaryDirectory(prefix="aikit-codex-update-") as folder:
        stage = Path(folder)
        (stage / ".aikit").mkdir()
        (stage / STATE_FILE).write_bytes((workspace / STATE_FILE).read_bytes())
        overrides = workspace / ".aikit/models.json"
        if overrides.exists():
            (stage / ".aikit/models.json").write_bytes(overrides.read_bytes())
        command([sys.executable, str(root / "scripts/plugin-init.py"), "--runtime", "codex", "--refresh-agents", "--workspace", str(stage)], stage)
        generated = read_json(stage / STATE_FILE)
        new_names = names(generated.get("codex_agents"), "новых агентов")
        if not new_names or set(new_names) != {path.stem for path in (stage / AGENTS_DIR).glob("*.toml")}:
            raise UpdateError("Пересборка не создала ожидаемый набор TOML-агентов")
        if generated.get("profiles") != state.get("profiles") or generated.get("packs", []) != state.get("packs", []):
            raise UpdateError("Пересборка изменила набор профилей или паков")
        for name in new_names:
            agent = tomllib.loads((stage / AGENTS_DIR / f"{name}.toml").read_text(encoding="utf-8"))
            if agent.get("name") != name or not agent.get("description") or not agent.get("developer_instructions"):
                raise UpdateError(f"Некорректное определение агента {name}")
        if read_json(workspace / STATE_FILE) != state or (overrides.read_bytes() if overrides.exists() else None) != ((stage / ".aikit/models.json").read_bytes() if (stage / ".aikit/models.json").exists() else None):
            raise UpdateError("Настройки проекта изменились во время обновления; повтори команду")
        updated_source(after, profiles, packs)
        if generated.get("codex_agents_version", after["aikit"]["version"]) != after["aikit"]["version"]:
            raise UpdateError("Версия пересобранных агентов не совпала с версией плагина")
        versions = {name: after[name]["version"] for name in required}
        promote(workspace, stage, previous, new_names, {**state, "codex_agents": new_names, "codex_agents_version": versions["aikit"], "codex_plugin_versions": versions})
    for name in required:
        print(f"{name}: {before[name]['version']} → {after[name]['version']}")
    print(f"Агенты Codex: {state.get('codex_agents_version', 'неизвестно')} → {versions['aikit']}, {len(new_names)} шт.")
    print("Открой новую сессию Codex. Если хуки изменились, одобри их повторно в /hooks.")
    return versions


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--codex-bin", default="codex", help="Codex executable, resolved through PATH")
    args = parser.parse_args()
    codex = shutil.which(args.codex_bin)
    if not codex:
        parser.error("Codex CLI не найден в PATH")
    try:
        update(Path(args.workspace).resolve(), codex)
    except (UpdateError, OSError, ValueError) as error:
        print(f"AIKit: обновление не завершено: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
