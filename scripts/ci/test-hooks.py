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

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parents[2] / "base" / "hooks" / "aikit_hook.py"
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


def main() -> int:
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
