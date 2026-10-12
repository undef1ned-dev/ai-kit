#!/usr/bin/env python3
"""
Install AIKit hooks into a project in the native format of each runtime.

The logic lives in one script, base/hooks/aikit_hook.py, copied to .aikit/hooks/ of the project.
Each runtime only gets the wiring that calls it:

    claude   — "hooks" in .claude/settings.json
    codex    — .codex/hooks.json (Codex runs project hooks after the user trusts them in /hooks)
    opencode — plugin .opencode/plugins/aikit-hooks.js; memory and PRODUCT.md go to "instructions"
               in opencode.json, because OpenCode plugins cannot add context at session start

Handlers that call aikit_hook.py are owned by the kit and replaced on every run;
the user's own hooks stay as they are.

Usage:
    python3 scripts/hooks_config.py <claude|codex|opencode> [--workspace .]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK_SOURCE = ROOT / "base" / "hooks" / "aikit_hook.py"
PLUGIN_SOURCE = ROOT / "base" / "hooks" / "opencode-plugin.js"
HOOK_TARGET = Path(".aikit") / "hooks" / "aikit_hook.py"
PLUGIN_TARGET = Path(".opencode") / "plugins" / "aikit-hooks.js"
OPENCODE_INSTRUCTIONS = [".aikit/memory/INDEX.md", "PRODUCT.md"]
OPENCODE_SCHEMA = "https://opencode.ai/config.json"
RUNTIMES = ("claude", "codex", "opencode")
HOOK_MARKER = "aikit_hook.py"

# event → (Claude Code matcher, Codex matcher, timeout in seconds, Codex status message)
EVENTS = {
    "SessionStart": (None, None, 30, "AIKit: память проекта"),
    "PreToolUse": ("Bash|Write|Edit|MultiEdit", "Bash|apply_patch", 30, "AIKit: проверка правил"),
    "PostToolUse": ("Write|Edit|MultiEdit", "apply_patch", 300, "AIKit: форматирование и линтер"),
    "Stop": (None, None, 600, "AIKit: тесты"),
}
CLAUDE_COMMAND = 'python3 "$CLAUDE_PROJECT_DIR/.aikit/hooks/aikit_hook.py"'
# Codex runs hooks in the session folder; the git root finds the project from a subfolder
CODEX_COMMAND = 'python3 "$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.aikit/hooks/aikit_hook.py"'
CODEX_COMMAND_WINDOWS = "python .aikit/hooks/aikit_hook.py"


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def is_kit_group(group: object) -> bool:
    handlers = group.get("hooks", []) if isinstance(group, dict) else []
    return any(HOOK_MARKER in str(handler.get("command", "")) for handler in handlers if isinstance(handler, dict))


def merge_hooks(config: dict, kit_groups: dict[str, dict]) -> dict:
    """Replace the kit's handler groups in a hooks section; groups of the user stay in place."""
    hooks = config.get("hooks") if isinstance(config.get("hooks"), dict) else {}
    for event in list(hooks):
        groups = [group for group in hooks[event] if not is_kit_group(group)] if isinstance(hooks[event], list) else hooks[event]
        if groups:
            hooks[event] = groups
        else:
            del hooks[event]
    for event, group in kit_groups.items():
        hooks.setdefault(event, []).append(group)
    config["hooks"] = hooks
    return config


def claude_groups() -> dict[str, dict]:
    groups = {}
    for event, (matcher, _, timeout, _) in EVENTS.items():
        group: dict = {"matcher": matcher} if matcher else {}
        group["hooks"] = [{"type": "command", "command": CLAUDE_COMMAND, "timeout": timeout}]
        groups[event] = group
    return groups


def codex_groups() -> dict[str, dict]:
    groups = {}
    for event, (_, matcher, timeout, status) in EVENTS.items():
        group: dict = {"matcher": matcher} if matcher else {}
        group["hooks"] = [
            {
                "type": "command",
                "command": CODEX_COMMAND,
                "commandWindows": CODEX_COMMAND_WINDOWS,
                "timeout": timeout,
                "statusMessage": status,
            }
        ]
        groups[event] = group
    return groups


def install_json_hooks(path: Path, groups: dict[str, dict]) -> bool:
    config = read_json(path)
    if config is None:
        print(f"! {path.name} не разобран как JSON — хуки AIKit не добавлены", file=sys.stderr)
        return False
    write_json(path, merge_hooks(config, groups))
    return True


def install_opencode(workspace: Path) -> bool:
    plugin = workspace / PLUGIN_TARGET
    plugin.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PLUGIN_SOURCE, plugin)
    config_path = workspace / "opencode.json"
    config = read_json(config_path)
    if config is None:
        print("! opencode.json не разобран как JSON (комментарии?) — память не добавлена в instructions", file=sys.stderr)
        return True
    config = config or {"$schema": OPENCODE_SCHEMA}
    instructions = config.get("instructions") if isinstance(config.get("instructions"), list) else []
    config["instructions"] = instructions + [item for item in OPENCODE_INSTRUCTIONS if item not in instructions]
    write_json(config_path, config)
    return True


def install(runtime: str, workspace: Path) -> bool:
    target = workspace / HOOK_TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HOOK_SOURCE, target)
    if runtime == "claude":
        return install_json_hooks(workspace / ".claude" / "settings.json", claude_groups())
    if runtime == "codex":
        return install_json_hooks(workspace / ".codex" / "hooks.json", codex_groups())
    return install_opencode(workspace)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install AIKit hooks in the runtime's native format")
    parser.add_argument("runtime", choices=RUNTIMES)
    parser.add_argument("--workspace", default=".")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    installed = install(args.runtime, Path(args.workspace).resolve())
    print(", ".join(EVENTS) if installed else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
