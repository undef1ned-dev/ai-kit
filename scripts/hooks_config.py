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
import base64
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK_SOURCE = ROOT / "base" / "hooks" / "aikit_hook.py"
PLUGIN_SOURCE = ROOT / "base" / "hooks" / "opencode-plugin.js"
HOOK_TARGET = Path(".aikit") / "hooks" / "aikit_hook.py"
CODEX_HOOK_SOURCE = ROOT / "base/codex/hooks/aikit_hook.py"
CODEX_HOOK_TARGET = Path(".aikit/hooks/codex/aikit_hook.py")
ANTIGRAVITY_HOOK_SOURCE = ROOT / "base/antigravity/hooks/aikit_hook.py"
ANTIGRAVITY_HOOK_TARGET = Path(".aikit/hooks/antigravity/aikit_hook.py")
PLUGIN_TARGET = Path(".opencode") / "plugins" / "aikit-hooks.js"
OPENCODE_INSTRUCTIONS = [".aikit/memory/INDEX.md", "PRODUCT.md"]
OPENCODE_SCHEMA = "https://opencode.ai/config.json"
RUNTIMES = ("claude", "codex", "opencode", "antigravity")
HOOK_MARKER = "aikit_hook.py"

# Independent runtime event contracts; the shared engine does not determine their wiring.
CLAUDE_EVENTS = {
    "SessionStart": (None, 30),
    "PreToolUse": ("Bash|Write|Edit|MultiEdit", 30),
    "PostToolUse": ("Write|Edit|MultiEdit", 300),
    "Stop": (None, 600),
}
CODEX_EVENTS = {
    "SessionStart": (None, 30, "AIKit: память проекта"),
    "PreToolUse": ("^(Bash|apply_patch)$", 30, "AIKit: проверка правил"),
    "PostToolUse": ("^apply_patch$", 300, "AIKit: форматирование и линтер"),
    "Stop": (None, 600, "AIKit: тесты"),
}
ANTIGRAVITY_EVENTS = {
    "SessionStart": (None, 30),
    "PreToolUse": ("run_command|write_file|edit_file", 30),
    "PostToolUse": ("write_file|edit_file", 300),
    "PostInvocation": (None, 30),
    "Stop": (None, 600),
}
EVENTS = CODEX_EVENTS
CLAUDE_COMMAND = 'python3 "$CLAUDE_PROJECT_DIR/.aikit/hooks/aikit_hook.py"'
# Codex runs hooks in the session folder; the git root finds the project from a subfolder
CODEX_COMMAND = 'python3 "$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.aikit/hooks/codex/aikit_hook.py"'
# On Windows Codex runs the hook in the session shell (powershell -Command) or cmd.exe, where $(...) and
# ${VAR} mean different things or nothing. The launcher is a python -c one-liner without shell syntax; its
# program is base64, so quotes and special characters never meet the shell.
# PowerShell 5.1 turns exit code 2 into 1, so the hook blocks with JSON (--deny-json in aikit_hook.py)
DENY_JSON_FLAG = "--deny-json"
PLUGIN_FLAG = "--plugin"
MIN_PYTHON = (3, 9)
# Python 2 and 3 must both parse it: "python" on PATH can be Python 2 or an older Python 3
WINDOWS_LAUNCHER_BODY = """import os, subprocess, sys
{find}
if not h:
    sys.exit(0)
args = {args!r}
if sys.version_info[:2] >= {minimum!r}:
    import runpy
    sys.argv = [h] + args
    runpy.run_path(h, run_name='__main__')
else:
    check = 'import sys;sys.exit(0 if sys.version_info[:2] >= {minimum!r} else 1)'
    data = getattr(sys.stdin, 'buffer', sys.stdin).read()
    for py in (['py', '-3'], ['python3']):
        try:
            if subprocess.call(py + ['-c', check]) != 0:
                continue
            run = subprocess.Popen(py + [h] + args, stdin=subprocess.PIPE)
        except OSError:
            continue
        run.communicate(data)
        sys.exit(run.returncode)
    sys.stderr.write('AIKit: need Python {minimum_text}+ for hooks, found ' + sys.version.split()[0] + '\\n')
    try:
        import tempfile, time
        folder = os.path.join(tempfile.gettempdir(), 'aikit-hooks')
        if not os.path.isdir(folder):
            os.makedirs(folder)
        note = open(os.path.join(folder, 'launch-error.txt'), 'w')
        note.write('no Python {minimum_text}+ for hooks: python on PATH is ' + sys.version.split()[0] + ' (' + sys.executable + '), py -3 and python3 did not fit; ' + time.strftime('%Y-%m-%d %H:%M:%S'))
        note.close()
    except Exception:
        pass
"""
# Looks for the script from the session cwd up (the git root of the project included)
ADAPTER_FIND = """h = None
d = os.getcwd()
while True:
    c = os.path.join(d, {target!r})
    if os.path.isfile(c):
        h = c
        break
    n = os.path.dirname(d)
    if n == d:
        break
    d = n"""


def windows_launcher(find: str, args: list[str], minimum: tuple[int, int] = MIN_PYTHON) -> str:
    """Hook command for Windows: runs the script with the first Python 3.9+ it can find."""
    body = WINDOWS_LAUNCHER_BODY.format(
        find=find, args=args, minimum=minimum, minimum_text=".".join(map(str, minimum)),
    )
    encoded = base64.b64encode(body.encode("utf-8")).decode("ascii")
    return "python -c \"import base64;exec(base64.b64decode('" + encoded + "'))\""


def antigravity_launcher(script_path: str, args: list[str]) -> str:
    """Cross-platform hook command for Antigravity without inner quotes (Windows cmd /c escapes quotes)."""
    tail = " ".join([script_path, *args])
    return f"python {tail} || python3 {tail}"


CODEX_COMMAND_WINDOWS = windows_launcher(ADAPTER_FIND.format(target=CODEX_HOOK_TARGET.as_posix()), [DENY_JSON_FLAG])
ANTIGRAVITY_ADAPTER_SCRIPT = "../" + ANTIGRAVITY_HOOK_TARGET.as_posix()
ANTIGRAVITY_PLUGIN_SCRIPT = "base/antigravity/hooks/aikit_hook.py"


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


def claude_groups(command: str = CLAUDE_COMMAND) -> dict[str, dict]:
    groups = {}
    for event, (matcher, timeout) in CLAUDE_EVENTS.items():
        group: dict = {"matcher": matcher} if matcher else {}
        group["hooks"] = [{"type": "command", "command": command, "timeout": timeout}]
        groups[event] = group
    return groups


def codex_groups(command: str = CODEX_COMMAND, command_windows: str = CODEX_COMMAND_WINDOWS) -> dict[str, dict]:
    groups = {}
    for event, (matcher, timeout, status) in CODEX_EVENTS.items():
        group: dict = {"matcher": matcher} if matcher else {}
        group["hooks"] = [
            {
                "type": "command",
                "command": command,
                "commandWindows": command_windows,
                "timeout": timeout,
                "statusMessage": status,
            }
        ]
        groups[event] = group
    return groups


def antigravity_groups(script_path: str = ANTIGRAVITY_ADAPTER_SCRIPT, extra_args: list[str] | None = None) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    base_args = list(extra_args or [])
    for event, (matcher, timeout) in ANTIGRAVITY_EVENTS.items():
        handler = {
            "type": "command",
            "command": antigravity_launcher(script_path, [*base_args, "--event", event]),
            "timeout": timeout,
        }
        if matcher:
            groups[event] = [{"matcher": matcher, "hooks": [handler]}]
        else:
            groups[event] = [handler]
    return groups


def install_antigravity_hooks(path: Path, script_path: str = ANTIGRAVITY_ADAPTER_SCRIPT, extra_args: list[str] | None = None) -> bool:
    config = read_json(path)
    if config is None:
        print(f"! {path.name} не разобран как JSON — хуки AIKit не добавлены", file=sys.stderr)
        return False
    config["aikit"] = antigravity_groups(script_path, extra_args)
    write_json(path, config)
    return True


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
        native = workspace / CODEX_HOOK_TARGET
        native.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CODEX_HOOK_SOURCE, native)
        return install_json_hooks(workspace / ".codex" / "hooks.json", codex_groups())
    if runtime == "antigravity":
        native = workspace / ANTIGRAVITY_HOOK_TARGET
        native.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ANTIGRAVITY_HOOK_SOURCE, native)
        return install_antigravity_hooks(workspace / ".agents" / "hooks.json")
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
