#!/usr/bin/env python3
"""Write project plugin settings and ship the opt-in native policy template."""

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "base/codex/settings.toml"
TARGET = Path(".codex/aikit-permissions.example.toml")
BEGIN = "# BEGIN AIKIT SETTINGS — managed by AIKit installer"
END = "# END AIKIT SETTINGS"
PLUGINS_BEGIN = "# BEGIN AIKIT PLUGINS — managed by AIKit setup"
PLUGINS_END = "# END AIKIT PLUGINS"


def install_codex_plugins(workspace: Path, plugin_ids: list[str]) -> None:
    import tomllib

    path = workspace / ".codex/config.toml"
    original = path.read_bytes().decode("utf-8") if path.exists() else ""
    pattern = re.compile(rf"^{re.escape(PLUGINS_BEGIN)}[^\S\r\n]*\r?\n.*?^{re.escape(PLUGINS_END)}[^\S\r\n]*(?:\r?\n|$)", re.S | re.M)
    user_text = pattern.sub("", original)
    plugins = tomllib.loads(user_text).get("plugins", {})
    if not isinstance(plugins, dict):
        raise ValueError("Ожидалась таблица plugins в .codex/config.toml")
    entries = [f"[plugins.{json.dumps(plugin_id)}]\nenabled = true" for plugin_id in plugin_ids if plugin_id not in plugins]
    updated = user_text
    if entries:
        block = "\n\n".join(entries)
        separator = "" if not user_text or user_text.endswith("\n\n") else "\n" if user_text.endswith("\n") else "\n\n"
        updated = f"{user_text}{separator}{PLUGINS_BEGIN}\n{block}\n{PLUGINS_END}\n"
    try:
        tomllib.loads(updated)
    except tomllib.TOMLDecodeError as error:
        raise ValueError("Не удалось добавить плагины в .codex/config.toml. Используй отдельные таблицы [plugins.\"имя@aikit\"]") from error
    if updated != original:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(updated.encode("utf-8"))


def install_codex(workspace: Path) -> bool:
    import tomllib

    path = workspace / ".codex/config.toml"
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    tomllib.loads(original)
    pattern = re.compile(rf"{re.escape(BEGIN)}.*?{re.escape(END)}\n?", re.S)
    user_text = pattern.sub("", original)
    user = tomllib.loads(user_text)
    native = SOURCE.read_text(encoding="utf-8").strip()
    payload = tomllib.loads(native)
    if set(payload) != {"permissions"} or set(payload["permissions"]) != {"aikit"}:
        raise ValueError("AIKit native settings may only define permissions.aikit")
    if user_text != original:
        if user.get("default_permissions") == "aikit":
            print("! Профиль aikit выбран явно; прежний блок сохранён. Проверь совместимость Codex перед ручным переносом", file=sys.stderr)
            return False
        path.write_bytes(user_text.encode("utf-8"))
    target = workspace / TARGET
    content = (native + "\n").encode("utf-8")
    if target.exists() and target.read_bytes() != content:
        print("! Шаблон aikit-permissions.example.toml изменён командой — сохранён", file=sys.stderr)
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return True
