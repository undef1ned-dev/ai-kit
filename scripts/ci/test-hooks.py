#!/usr/bin/env python3
"""
Scenario tests of the AIKit hook script base/hooks/aikit_hook.py.

Each scenario feeds a hook event (the Claude Code / Codex JSON shape) to the script in a temporary
git project and checks the result: blocked or not, lint feedback, test failures, session context.
Profile commands are replaced by small Python scripts, so no Node.js or uv is needed.

Usage:
    python3 scripts/ci/test-hooks.py
"""

from __future__ import annotations

import datetime
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
HOOK = KIT_ROOT / "base" / "hooks" / "aikit_hook.py"
BLOCKED = 2
PYTHON = f'"{sys.executable}"'

PRE_BASH = [
    ("коммит по Conventional Commits", 'git commit -m "feat(auth): добавлена авторизация"', 0),
    ("коммит не по формату", 'git commit -m "added stuff"', BLOCKED),
    ("коммит с соавтором", 'git commit -m "fix: x" -m "Co-Authored-By: Bot <bot@example.com>"', BLOCKED),
    ("коммит с приписной Generated with", 'git commit -m "fix: x\n\nGenerated with Tool"', BLOCKED),
    ("коммит через heredoc", "git add a.py && git commit -m \"$(cat <<'EOF'\nfix: исправлено падение\n\ndon't panic\nEOF\n)\"", 0),
    ("heredoc с соавтором", "git commit -m \"$(cat <<'EOF'\nfix: ok\n\nCo-Authored-By: X <x@y>\nEOF\n)\"", BLOCKED),
    ("heredoc не по формату", "git commit -m \"$(cat <<'EOF'\nWIP\nEOF\n)\"", BLOCKED),
    ("amend без сообщения", "git commit --amend --no-edit", 0),
    ("merge-коммит", 'git commit -m "Merge branch main"', 0),
    ("git -C перед командой", 'git -C sub commit -m "chore: обновлены зависимости"', 0),
    ("; и && внутри сообщения", 'git commit -m "fix: работа с ; и && в тексте"', 0),
    ("ветка по Conventional Branch", "git checkout -b feat/oauth-login", 0),
    ("ветка не по формату", "git checkout -b MyBranch", BLOCKED),
    ("switch -c не по формату", "git switch -c feature_x", BLOCKED),
    ("ветка релиза с версией", "git switch -c release/v1.2.0", 0),
    ("git branch новая не по формату", "git branch Foo", BLOCKED),
    ("список веток", "git branch -a", 0),
    ("удаление ветки", "git branch -D Foo", 0),
    ("переименование ветки", "git branch -m fix/thing", 0),
    ("worktree с веткой агента", "git worktree add ../x -b claude/abc-123", 0),
    ("git add .env", "git add .env", BLOCKED),
    ("git add -A с .env", "git add -A", BLOCKED),
    ("git add . с .env", "git add .", BLOCKED),
    ("git add обычного файла", "git add a.py", 0),
    ("git add .env.example", "git add .env.example", 0),
    ("git -C подпапка add -A не видит .env корня", "git -C sub add -A", 0),
    ("echo в .env", "echo X=1 >> .env", BLOCKED),
    ("echo в .env.local", "echo X=1 > config/.env.local", BLOCKED),
    ("секрет в echo", "echo AKIAABCDEFGHIJKLMNOP > key.txt", BLOCKED),
    ("Set-Content -LiteralPath в .env.local", "Set-Content -LiteralPath .env.local -Value X=1", BLOCKED),
    ("Set-Content позиционно в .env", "Set-Content .env 'X=1'", BLOCKED),
    ("Add-Content -Path: в .env", "Add-Content -Path:'.\\.env' -Value X=1", BLOCKED),
    ("Out-File в .env после конвейера", "'X=1' | Out-File -Encoding utf8 -FilePath config\\.env.local", BLOCKED),
    ("New-Item .env со значением", "New-Item -ItemType File -Name .env -Value X=1 -Force", BLOCKED),
    ("Tee-Object в .env", "'X=1' | Tee-Object -FilePath .env", BLOCKED),
    ("[IO.File]::WriteAllText в .env", "[System.IO.File]::WriteAllText('.env', 'X=1')", BLOCKED),
    ("powershell -Command с Set-Content", 'powershell.exe -NoProfile -Command "Set-Content -Path .env -Value X=1"', BLOCKED),
    ("Set-Content в .env.example", "Set-Content -Path .env.example -Value X=", 0),
    ("Set-Content читает .env в другой файл", "Set-Content -Path out.txt -Value (Get-Content .env)", 0),
    ("Get-Content без записи", "Get-Content -Encoding UTF8 .env.example", 0),
    ("секрет в Set-Content", "Set-Content -Path key.txt -Value AKIA" + "ABCDEFGHIJKLMNOP", BLOCKED),
    ("незакрытая кавычка", "echo 'oops", 0),
    ("обычная команда", "ls -la", 0),
]

PRE_FILES = [
    ("Write в .env", {"tool_name": "Write", "tool_input": {"file_path": ".env", "content": "A=1"}}, BLOCKED),
    ("Write в .env.example", {"tool_name": "Write", "tool_input": {"file_path": ".env.example", "content": "A="}}, 0),
    ("Write с токеном GitHub", {"tool_name": "Write", "tool_input": {"file_path": "a.ts", "content": "const k = 'ghp_" + "a" * 36 + "'"}}, BLOCKED),
    ("Edit с приватным ключом", {"tool_name": "Edit", "tool_input": {"file_path": "a.ts", "old_string": "x", "new_string": "-----BEGIN RSA PRIVATE KEY-----"}}, BLOCKED),
    ("MultiEdit без секретов", {"tool_name": "MultiEdit", "tool_input": {"file_path": "a.ts", "edits": [{"old_string": "a", "new_string": "b"}]}}, 0),
    ("apply_patch добавляет .env", {"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** Add File: .env\n+A=1\n*** End Patch"}}, BLOCKED),
    ("apply_patch с ключом", {"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** Update File: src/a.py\n@@\n+key = 'sk-ant-" + "b" * 30 + "'\n*** End Patch"}}, BLOCKED),
    ("apply_patch обычный", {"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** Update File: src/a.py\n@@\n+x = 1\n*** End Patch"}}, 0),
]


def load_hook():
    spec = importlib.util.spec_from_file_location("aikit_hook", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def codex_windows_commands() -> dict[str, str]:
    """commandWindows of the Codex hooks: the adapter (.codex/hooks.json) and the core plugin."""
    sys.path.insert(0, str(KIT_ROOT / "scripts"))
    import hooks_config

    spec = importlib.util.spec_from_file_location("aikit_build_plugins", KIT_ROOT / "scripts" / "build-plugins.py")
    plugins = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugins)
    return {"адаптер": hooks_config.CODEX_COMMAND_WINDOWS, "плагин": plugins.CODEX_HOOK_COMMAND_WINDOWS}


def python_shim(folder: Path) -> None:
    """`python` ahead on PATH that runs this interpreter: on a developer machine `python` may be Python 2."""
    posix = folder / "python"
    posix.write_bytes(f'#!/bin/sh\nexec "{Path(sys.executable).as_posix()}" "$@"\n'.encode("utf-8"))
    posix.chmod(0o755)
    (folder / "python.cmd").write_bytes(f'@"{sys.executable}" %*\r\n'.encode("utf-8"))


def hook_shells(command: str) -> list[tuple[str, list[str] | str]]:
    """The shells Codex runs a hook command in: cmd.exe /C or the session PowerShell on Windows, sh elsewhere."""
    if os.name != "nt":
        return [("sh", ["/bin/sh", "-c", command])]
    shells: list[tuple[str, list[str] | str]] = [("cmd.exe", command)]
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if powershell:
        shells.append(("PowerShell", [powershell, "-NoProfile", "-Command", command]))
    return shells


def run_in_shell(shell_command: list[str] | str, cwd: Path, event: dict, env: dict[str, str]) -> tuple[int, str]:
    result = subprocess.run(
        shell_command, shell=isinstance(shell_command, str), cwd=cwd, env=env,
        input=json.dumps(event).encode("utf-8"), capture_output=True, timeout=60,
    )
    return result.returncode, result.stdout.decode("utf-8", errors="replace").strip()


def old_python_shim(folder: Path) -> None:
    """`python` that reports version 2.7 and runs the -c program of the launcher, and `python3` that is this interpreter."""
    fake = folder / "fake_python.py"
    fake.write_text(
        "import sys\nsys.version_info = (2, 7, 18, 'final', 0)\nsys.version = '2.7.18'\n"
        "assert sys.argv[1] == '-c'\nexec(sys.argv[2])\n",
        encoding="utf-8",
    )
    (folder / "python").write_bytes(f'#!/bin/sh\nexec "{Path(sys.executable).as_posix()}" "{fake.as_posix()}" "$@"\n'.encode("utf-8"))
    (folder / "python").chmod(0o755)
    (folder / "python3").write_bytes(f'#!/bin/sh\nexec "{Path(sys.executable).as_posix()}" "$@"\n'.encode("utf-8"))
    (folder / "python3").chmod(0o755)


def check_old_python(project, expect) -> None:
    """The launcher hands the event to a suitable Python 3.9+ when `python` is old, and never breaks the action."""
    sys.path.insert(0, str(KIT_ROOT / "scripts"))
    import hooks_config

    event = {"hook_event_name": "PreToolUse", "session_id": "old", "cwd": str(project.root), "tool_name": "apply_patch",
             "tool_input": {"command": "*** Begin Patch\n*** Add File: .env\n+A=1\n*** End Patch"}}
    find = hooks_config.ADAPTER_FIND.format(target=hooks_config.HOOK_TARGET.as_posix())
    unreachable = hooks_config.windows_launcher(find, [hooks_config.DENY_JSON_FLAG], minimum=(99, 0))
    with tempfile.TemporaryDirectory() as shim:
        python_shim(Path(shim))
        env = {**os.environ, "PATH": f"{shim}{os.pathsep}{os.environ.get('PATH', '')}"}
        for shell, shell_command in hook_shells(unreachable):
            code, stdout = run_in_shell(shell_command, project.root, event, env)
            expect(f"{shell}: нет подходящего Python — действие не блокируется", code == 0 and not stdout, f"код {code}, {stdout}")
        status = hook_status(project.root)
        expect("--status: лаунчер без Python 3.9+ оставляет launcher-error", status["state"] == "launcher-error", str(status))
        project.run({"hook_event_name": "SessionStart"})
        expect("--status: запуск хука снимает launcher-error", hook_status(project.root)["state"] == "ok")
    if os.name == "nt":
        return
    with tempfile.TemporaryDirectory() as shim:
        old_python_shim(Path(shim))
        env = {**os.environ, "PATH": f"{shim}{os.pathsep}{os.environ.get('PATH', '')}"}
        for shell, shell_command in hook_shells(hooks_config.CODEX_COMMAND_WINDOWS):
            code, stdout = run_in_shell(shell_command, project.root, event, env)
            expect(f"{shell}: python 2.7 передаёт событие Python 3 (deny в JSON)", denied_by_json(code, stdout), f"код {code}, {stdout}")


def hook_status(root: Path) -> dict:
    result = subprocess.run([sys.executable, str(HOOK), "--status"], capture_output=True, cwd=root)
    return json.loads(result.stdout.decode("utf-8"))


def check_run_marks(expect) -> None:
    """Every hook run leaves a mark that /aikit:setup reads through --status."""
    with tempfile.TemporaryDirectory() as temp:
        fresh = Project(Path(temp))
        expect("--status: до первого запуска отметки нет", hook_status(fresh.root)["state"] == "no-mark")
        fresh.run({"hook_event_name": "SessionStart"})
        status = hook_status(fresh.root)
        expect("--status: после SessionStart хуки работают", status["state"] == "ok" and "SessionStart" in status["events"], str(status))
        expect("--status: записан интерпретатор", bool(status.get("python")) and bool(status.get("executable")), str(status))
        fresh.run({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": "SECRET_TOOL_INPUT"})
        status = hook_status(fresh.root)
        expect("--status: внутренняя ошибка хука видна", status["state"] == "internal-error" and status["last_error"]["event"] == "PreToolUse", str(status))
        expect("--status: в ошибке нет содержимого события", "SECRET_TOOL_INPUT" not in json.dumps(status.get("last_error", {})))
        fresh.run({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}})
        expect("--status: успешный запуск снимает ошибку", hook_status(fresh.root)["state"] == "ok")


def denied_by_json(code: int, stdout: str) -> bool:
    """PreToolUse block that survives powershell -Command: exit 0 and permissionDecision deny."""
    if code != 0 or not stdout:
        return False
    return json.loads(stdout).get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


class Project:
    def __init__(self, root: Path) -> None:
        self.root = root
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
        (root / ".aikit" / "memory").mkdir(parents=True)
        (root / "sub").mkdir()
        (root / "sub" / "a.py").write_text("x = 1\n", encoding="utf-8")

    def run(self, event: dict, session: str = "s1", flags: tuple[str, ...] = ()) -> tuple[int, dict, str]:
        event = {"cwd": str(self.root), "session_id": session, **event}
        result = subprocess.run(
            [sys.executable, str(HOOK), *flags], input=json.dumps(event).encode("utf-8"), capture_output=True, cwd=self.root
        )
        stdout = result.stdout.decode("utf-8").strip()
        return result.returncode, json.loads(stdout) if stdout else {}, result.stderr.decode("utf-8")

    def set_profile(self, commands: dict[str, str]) -> None:
        profile = {"root": "web", "code_extensions": [".vue", ".ts"], "commands": commands}
        (self.root / ".aikit" / "profiles.json").write_text(json.dumps({"profiles": {"vue-nuxt": profile}}), encoding="utf-8")


REFRESH_WAIT_SECONDS = 15
STALE_CHECKED_AT = "2020-01-01T00:00:00+00:00"
# Nothing listens on the discard port: an instant "offline" without real network
OFFLINE_URL = "http://127.0.0.1:9/VERSION"


def check_update_notice(project: Project, expect) -> None:
    """The hook of an installed plugin (its root holds VERSION) against a cache and a local "remote" VERSION."""
    with tempfile.TemporaryDirectory() as temp:
        temp_dir = Path(temp)
        plugin_hook = temp_dir / "plugin" / "base" / "hooks" / "aikit_hook.py"
        plugin_hook.parent.mkdir(parents=True)
        shutil.copyfile(HOOK, plugin_hook)
        (temp_dir / "plugin" / "VERSION").write_bytes(b"0.2.0\n")
        remote = temp_dir / "remote-VERSION"
        cache = temp_dir / "cache" / "update-check.json"
        base_env = {key: value for key, value in os.environ.items() if key not in {
            "CLAUDE_PLUGIN_ROOT", "PLUGIN_ROOT", "AIKIT_NO_UPDATE_CHECK", "CLAUDE_PROJECT_DIR",
        }}
        base_env.update({"AIKIT_UPDATE_URL": remote.as_uri(), "AIKIT_UPDATE_CACHE": str(cache), "CLAUDE_PLUGIN_ROOT": str(temp_dir / "plugin")})

        def session(cwd: Path = project.root, **env: str) -> dict:
            event = {"hook_event_name": "SessionStart", "source": "startup", "session_id": "upd", "cwd": str(cwd)}
            result = subprocess.run(
                [sys.executable, str(plugin_hook), "--plugin"], input=json.dumps(event).encode("utf-8"),
                capture_output=True, cwd=cwd, env={**base_env, **env}, timeout=30,
            )
            stdout = result.stdout.decode("utf-8").strip()
            return json.loads(stdout) if stdout else {}

        def write_cache(**fields: str) -> None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(json.dumps(fields).encode("utf-8"))

        def read_cache() -> dict:
            return json.loads(cache.read_text(encoding="utf-8")) if cache.is_file() else {}

        def wait_for_cache(condition) -> bool:
            deadline = time.monotonic() + REFRESH_WAIT_SECONDS
            while time.monotonic() < deadline:
                try:
                    if condition(read_cache()):
                        return True
                except (OSError, json.JSONDecodeError):
                    pass
                time.sleep(0.2)
            return False

        fresh = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        remote.write_bytes(b"0.3.0\n")
        output = session()
        expect("нет кэша — сообщения нет, старт не ждёт сети", "systemMessage" not in output, str(output))
        expect("нет кэша — версия забрана в фоне", wait_for_cache(lambda data: data.get("remote_version") == "0.3.0"), str(read_cache()))

        write_cache(checked_at=fresh, remote_version="0.3.0")
        output = session()
        message = output.get("systemMessage", "")
        expect("есть обновление — systemMessage с версиями и командами", "0.3.0" in message and "у вас 0.2.0" in message and "codex plugin marketplace upgrade" in message, str(output))
        context = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        expect("уведомление не попадает в контекст модели Claude", "0.3.0" not in context, context)
        expect("версия отмечена как показанная", read_cache().get("notified_version") == "0.3.0", str(read_cache()))
        output = session()
        expect("по той же версии второй раз не уведомляет", "systemMessage" not in output, str(output))

        write_cache(checked_at=fresh, remote_version="0.2.0")
        expect("версия в main та же — сообщения нет", "systemMessage" not in session())
        write_cache(checked_at=fresh, remote_version="0.1.9")
        expect("в main версия старее — сообщения нет", "systemMessage" not in session())

        write_cache(checked_at=STALE_CHECKED_AT, remote_version="0.2.0", notified_version="0.3.0")
        remote.write_bytes(b"0.4.0\n")
        output = session()
        expect("кэш устарел — сессия читает старое значение", "systemMessage" not in output, str(output))
        expect("кэш устарел — обновлён в фоне", wait_for_cache(lambda data: data.get("remote_version") == "0.4.0" and data.get("checked_at") != STALE_CHECKED_AT), str(read_cache()))
        expect("после обновления кэша — уведомление о новой версии", "0.4.0" in session().get("systemMessage", ""))

        write_cache(checked_at=STALE_CHECKED_AT, remote_version="0.4.0", notified_version="0.4.0")
        result = subprocess.run(
            [sys.executable, str(plugin_hook), "--refresh-update-cache"], capture_output=True,
            env={**base_env, "AIKIT_UPDATE_URL": OFFLINE_URL}, timeout=30,
        )
        data = read_cache()
        expect(
            "офлайн — молча, прошлое значение остаётся, проверка отложена на сутки",
            result.returncode == 0 and not result.stdout and not result.stderr
            and data.get("remote_version") == "0.4.0" and data.get("checked_at") != STALE_CHECKED_AT,
            f"{result.returncode} {result.stderr!r} {data}",
        )

        write_cache(checked_at=fresh, remote_version="0.5.0")
        expect("AIKIT_NO_UPDATE_CHECK=1 — без уведомления", "systemMessage" not in session(AIKIT_NO_UPDATE_CHECK="1"))
        settings = project.root / ".aikit" / "settings.json"
        settings.write_bytes(b'{"commit": "ask", "update_check": false}\n')
        expect("update_check: false в .aikit/settings.json — без уведомления", "systemMessage" not in session())
        settings.unlink()
        expect("cache не тронут при отключённой проверке", read_cache().get("notified_version") is None, str(read_cache()))

        codex_output = session(CLAUDE_PLUGIN_ROOT="", PLUGIN_ROOT=str(temp_dir / "plugin"))
        context = codex_output.get("hookSpecificOutput", {}).get("additionalContext", "")
        expect("Codex — запасной путь: просьба передать уведомление в additionalContext", "0.5.0" in codex_output.get("systemMessage", "") and "0.5.0" in context, str(codex_output))

        write_cache(checked_at=fresh, remote_version="0.6.0")
        with tempfile.TemporaryDirectory() as other:
            expect("проект без .aikit/ — хук молчит", session(cwd=Path(other)) == {})
        expect("без .aikit/ версия не отмечена", read_cache().get("notified_version") is None, str(read_cache()))
        code, output, _ = project.run({"hook_event_name": "SessionStart", "source": "startup"})
        expect("хук установщика (без --plugin) обновления не проверяет", "systemMessage" not in output, str(output))


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    # run marks and launcher notes go to the temp folder: keep them away from the real one
    isolated_temp = tempfile.mkdtemp(prefix="aikit-test-temp-")
    for name in ("TEMP", "TMP", "TMPDIR"):
        os.environ[name] = isolated_temp
    tempfile.tempdir = isolated_temp
    failures: list[str] = []

    def expect(name: str, condition: bool, details: str = "") -> None:
        print(f"  {'✓' if condition else '✗'} {name}")
        if not condition:
            failures.append(f"{name}: {details}")

    with tempfile.TemporaryDirectory() as temp:
        project = Project(Path(temp))

        print("▶ PreToolUse: команды")
        for name, command, expected in PRE_BASH:
            code, _, stderr = project.run({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}})
            expect(name, code == expected, f"код {code}, ожидался {expected}; {stderr.strip()}")

        print("▶ PreToolUse: запись файлов")
        for name, event, expected in PRE_FILES:
            code, _, stderr = project.run({"hook_event_name": "PreToolUse", **event})
            expect(name, code == expected, f"код {code}, ожидался {expected}; {stderr.strip()}")

        print("▶ PostToolUse и Stop: команды профиля")
        web = project.root / "web"
        (web / "components").mkdir(parents=True)
        (web / "fmt.py").write_text(
            "import sys, pathlib\nfor f in sys.argv[1:]:\n    p = pathlib.Path(f); p.write_text(p.read_text().strip() + chr(10))\n",
            encoding="utf-8",
        )
        (web / "lint.py").write_text("import sys\nprint('no-unused-vars in', *sys.argv[1:])\nsys.exit(1)\n", encoding="utf-8")
        (web / "fail.py").write_text("print('1 failed: test_cart')\nraise SystemExit(1)\n", encoding="utf-8")
        project.set_profile({"format": f"{PYTHON} fmt.py {{files}}", "lint": f"{PYTHON} lint.py {{files}}", "test": f"{PYTHON} fail.py"})
        component = web / "components" / "Cart.vue"
        component.write_text("<template/>\n\n\n", encoding="utf-8")
        (web / "README.md").write_text("docs\n", encoding="utf-8")

        _, output, _ = project.run({"hook_event_name": "Stop"})
        expect("Stop без изменений кода ничего не делает", output == {}, str(output))
        _, output, _ = project.run({"hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_input": {"file_path": "web/README.md"}})
        expect("не код профиля — линтер не запускается", output == {}, str(output))
        _, output, _ = project.run({"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": str(component)}})
        context = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        expect("форматтер профиля применён к файлу", component.read_text(encoding="utf-8") == "<template/>\n")
        expect("замечания линтера возвращены агенту", "no-unused-vars in components/Cart.vue" in context, context)
        _, output, _ = project.run({"hook_event_name": "Stop"})
        expect("упавшие тесты продолжают работу агента", output.get("decision") == "block" and "test_cart" in output.get("reason", ""), str(output))
        _, output, _ = project.run({"hook_event_name": "Stop"})
        expect("после прогона тесты не запускаются повторно", output == {}, str(output))
        project.run({"hook_event_name": "PostToolUse", "tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** Update File: web/components/Cart.vue\n+x\n*** End Patch"}})
        _, output, _ = project.run({"hook_event_name": "Stop", "stop_hook_active": True})
        expect("повторный Stop не зацикливает агента", "decision" not in output and "systemMessage" in output, str(output))

        project.set_profile({"test": "aikit-missing-tool-xyz --run"})
        project.run({"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": str(component)}})
        _, output, _ = project.run({"hook_event_name": "Stop"})
        expect("нет инструмента тестов — напоминание вместо блокировки", "decision" not in output and "systemMessage" in output, str(output))

        # Gradle and Maven wrappers: ./gradlew in bash, gradlew.bat in cmd.exe (the hook shell on Windows)
        wrapper = web / "gradlew"
        wrapper.write_bytes(b'#!/bin/sh\necho WRAPPER-FAIL "$@"\nexit 1\n')
        wrapper.chmod(0o755)
        (web / "gradlew.bat").write_bytes(b"@echo off\r\necho WRAPPER-FAIL %*\r\nexit /b 1\r\n")
        project.set_profile({"test": "./gradlew test"})
        project.run({"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": str(component)}})
        _, output, _ = project.run({"hook_event_name": "Stop"})
        expect("./gradlew запускается и на Windows (gradlew.bat)", "WRAPPER-FAIL test" in output.get("reason", ""), str(output))
        hook = load_hook()
        expect("./gradlew с .bat рядом → .\\gradlew", hook.windows_wrappers("./gradlew build && ./gradlew test", web) == ".\\gradlew build && .\\gradlew test")
        expect("./скрипт без .bat/.cmd не меняется", hook.windows_wrappers("./run.sh --fast", web) == "./run.sh --fast")
        expect("пути внутри аргументов не меняются", hook.windows_wrappers("python3 x.py ./gradlew-notes", web) == "python3 x.py ./gradlew-notes")

        for index in range(8):
            path = web / "components" / f"Item{index}.vue"
            path.write_text("<template/>\n", encoding="utf-8")
            project.run({"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": str(path)}}, session="big")
        _, output, _ = project.run({"hook_event_name": "Stop"}, session="big")
        expect("после крупной задачи предложен /capture-memory", "/capture-memory" in output.get("systemMessage", ""), str(output))

        memory = project.root / ".aikit" / "memory"
        memory.rename(memory.with_name("memory-off"))
        for index in range(8):
            project.run({"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": str(web / "components" / f"Item{index}.vue")}}, session="no-memory")
        _, output, _ = project.run({"hook_event_name": "Stop"}, session="no-memory")
        expect("без .aikit/memory/ (репозиторий кита) /capture-memory не предлагается", "/capture-memory" not in output.get("systemMessage", ""), str(output))
        memory.with_name("memory-off").rename(memory)

        print_cwd_and_fail = f'{PYTHON} -c "import os; print(os.getcwd()); raise SystemExit(1)"'
        project.set_profile({"lint": f"{print_cwd_and_fail} {{files}}", "test": print_cwd_and_fail})
        worktree_file = project.root / ".aikit" / "worktrees" / "feat-cart" / "web" / "components" / "Cart.vue"
        worktree_file.parent.mkdir(parents=True)
        worktree_file.write_text("<template/>\n", encoding="utf-8")
        _, output, _ = project.run({"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": str(worktree_file)}}, session="wt")
        context = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        expect("файл в worktree — линтер в папке профиля внутри worktree", str(Path("feat-cart") / "web") in context, context)
        _, output, _ = project.run({"hook_event_name": "Stop"}, session="wt")
        reason = output.get("reason", "")
        expect("тесты после правки в worktree запускаются в нём", ".aikit/worktrees/feat-cart/web" in reason, reason)

        print("▶ SessionStart: память и PRODUCT.md")
        _, output, _ = project.run({"hook_event_name": "SessionStart", "source": "startup"})
        expect("пустая память не добавляется", output == {}, str(output))
        (project.root / ".aikit" / "memory" / "INDEX.md").write_text("# Index\n- решение: состояние корзины в Pinia\n", encoding="utf-8")
        (project.root / "PRODUCT.md").write_text("# Магазин\nПродаём книги.\n", encoding="utf-8")
        _, output, _ = project.run({"hook_event_name": "SessionStart", "source": "startup"})
        context = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        expect("память и PRODUCT.md добавлены в контекст", "состояние корзины" in context and "Продаём книги" in context, context)

        print("▶ Хук из плагина (--plugin)")
        commit_event = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": 'git commit -m "wip"'}}
        code, _, _ = project.run(commit_event, flags=("--plugin",))
        expect("в проекте с .aikit/ правила действуют", code == BLOCKED)
        with tempfile.TemporaryDirectory() as other:
            outsider = Path(other)
            subprocess.run(["git", "init", "-q"], cwd=outsider, check=True)
            event = {**commit_event, "cwd": str(outsider), "session_id": "s1"}
            result = subprocess.run(
                [sys.executable, str(HOOK), "--plugin"], input=json.dumps(event).encode("utf-8"), capture_output=True, cwd=outsider
            )
            expect("в проекте без .aikit/ хук ничего не проверяет", result.returncode == 0 and not result.stdout.strip())
        code, output, _ = project.run(commit_event, flags=("--deny-json",))
        expect("--deny-json: блокировка через permissionDecision deny и код 0", code == 0 and output.get("hookSpecificOutput", {}).get("permissionDecision") == "deny", str(output))

        print("▶ Уведомление об обновлении (SessionStart плагина)")
        check_update_notice(project, expect)

        print("▶ Команды хуков Codex для Windows (commandWindows) из подпапки проекта")
        installed = project.root / ".aikit" / "hooks" / "aikit_hook.py"
        installed.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HOOK, installed)
        subfolder = project.root / "sub"
        env_patch = {"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** Add File: .env\n+A=1\n*** End Patch"}}
        with tempfile.TemporaryDirectory() as shim, tempfile.TemporaryDirectory() as other:
            python_shim(Path(shim))
            env = {**os.environ, "PATH": f"{shim}{os.pathsep}{os.environ.get('PATH', '')}", "PLUGIN_ROOT": str(KIT_ROOT)}
            env.pop("CLAUDE_PROJECT_DIR", None)
            for kind, command in codex_windows_commands().items():
                for shell, shell_command in hook_shells(command):
                    event = {"hook_event_name": "PreToolUse", "session_id": "win", "cwd": str(subfolder), **env_patch}
                    code, stdout = run_in_shell(shell_command, subfolder, event, env)
                    expect(f"{kind}, {shell}: из подпапки запись .env заблокирована (deny в JSON)", denied_by_json(code, stdout), f"код {code}, {stdout}")
                    code, stdout = run_in_shell(shell_command, Path(other), {**event, "cwd": other}, env)
                    expect(f"{kind}, {shell}: вне проекта действие пропущено", code == 0 and not stdout, f"код {code}, {stdout}")

        print("▶ Отметки запусков хуков (--status)")
        check_run_marks(expect)

        print("▶ Лаунчер Windows: python на PATH старый или неподходящий")
        check_old_python(project, expect)

        print("▶ Устойчивость")
        code, _, _ = project.run({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": None})
        expect("кривой ввод не блокирует действие", code == 0)

    if failures:
        print(f"✗ Хуки: не пройдено {len(failures)}")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("✓ Хуки: все сценарии пройдены")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
