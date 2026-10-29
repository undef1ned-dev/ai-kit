#!/usr/bin/env python3
"""Ship an opt-in native policy template without changing the active Codex configuration."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "base/codex/settings.toml"
TARGET = Path(".codex/aikit-permissions.example.toml")
BEGIN = "# BEGIN AIKIT SETTINGS — managed by AIKit installer"
END = "# END AIKIT SETTINGS"


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
