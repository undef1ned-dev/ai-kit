#!/usr/bin/env python3
"""
Self-test of scripts/run-evals.py without model calls.

    - the case files of evals/ parse and pass --check;
    - regex and file_exists graders score the way claude plugin eval scores them;
    - the Codex path prepares the project with the adapter installer, calls `codex exec`
      with the case prompt and grades the reply — a fake codex stands in for the real CLI.

Usage:
    python3 scripts/ci/test-run-evals.py
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import os
import json
import subprocess
from unittest.mock import patch
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FAKE_CODEX = r'''
import json, os, sys
from pathlib import Path

args = sys.argv[1:]
workspace = Path(args[args.index("--cd") + 1])
last_message = Path(args[args.index("--output-last-message") + 1])
if not (workspace / "AGENTS.md").exists() or not (workspace / ".agents" / "skills").is_dir():
    print("kit is not installed in the workspace", file=sys.stderr)
    sys.exit(3)
prompt = args[-1]
for name, content in json.loads(os.environ.get("FAKE_CODEX_FILES", "{}")).items():
    (workspace / name).parent.mkdir(parents=True, exist_ok=True)
    (workspace / name).write_text(content, encoding="utf-8")
last_message.write_text(os.environ.get("FAKE_CODEX_REPLY", ""), encoding="utf-8")
print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": prompt}}, ensure_ascii=False))
print(json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": "cat .agents/skills/git-commit/SKILL.md", "status": "completed", "exit_code": 0}}))
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}}))
'''

failures = 0


def check(condition: bool, label: str) -> None:
    global failures
    print(f"  {'✓' if condition else '✗'} {label}")
    if not condition:
        failures += 1


def load_runner():
    spec = importlib.util.spec_from_file_location("run_evals", ROOT / "scripts" / "run-evals.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def codex_run(runner, case: dict, fake: Path, reply: str, files: dict | None = None) -> dict:
    import json
    import os

    os.environ["FAKE_CODEX_REPLY"] = reply
    os.environ["FAKE_CODEX_FILES"] = json.dumps(files or {}, ensure_ascii=False)
    args = argparse.Namespace(codex_model=None, keep_temp=False)
    return runner.run_codex_case(case, [sys.executable, str(fake)], args)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    runner = load_runner()

    print("▶ Разбор кейсов")
    check(runner.parse_yaml('a: 1\nb: [x, "y, z"]\nt: { source: file, path: a/b.vue }\nctx:\n  s: setup.sh') == {
        "a": 1, "b": ["x", "y, z"], "t": {"source": "file", "path": "a/b.vue"}, "ctx": {"s": "setup.sh"},
    }, "YAML: скаляры, списки, словари в строку, вложенный блок")
    check(runner.parse_scalar("'a''b'") == "a'b", "YAML: одинарные кавычки и '' внутри")
    cases = runner.discover_cases()
    check(runner.run_check(cases) == 0, "evals/ проходит --check")
    by_name = {case["name"]: case for case in cases}
    check(runner.select_cases(cases, ["core"], None) == [c for c in cases if c["group"] == "core"], "--profile core выбирает группу core")
    check([c["name"] for c in runner.select_cases(cases, [], "review-*")] == sorted(
        [c["name"] for c in cases if c["name"].startswith("review-")], key=[c["name"] for c in cases].index,
    ), "--case фильтрует по маске имени")

    print("▶ Выбор групп")
    check(runner.resolve_groups(["vue-nuxt"], cases) == ["vue-nuxt"], "один профиль")
    check(runner.resolve_groups(["all", "vue-nuxt"], cases) == [], "all — все группы")
    with contextlib.redirect_stderr(io.StringIO()) as error:
        typo = runner.resolve_groups(["vue-nux"], cases)
    check(typo is None and "vue-nux" in error.getvalue(), "опечатка в имени — ошибка, а не прогон всего набора")
    check(runner.changed_groups(["profiles/vue-nuxt/agents/vue-reviewer.md"], cases) == ["vue-nuxt"], "правка профиля — только его группа")
    check(runner.changed_groups(["evals/fixtures/nuxt-app/components/users/UserList.vue"], cases) == ["core", "vue-nuxt"], "правка фикстуры — группы, которые её используют")
    check(runner.changed_groups(["evals/vue-nuxt/new-component/prompt.md"], cases) == ["vue-nuxt"], "правка кейса — его группа")
    check(runner.changed_groups(["base/skills/git-commit/SKILL.md"], cases) == runner.known_groups(cases), "правка base — все группы")
    check(runner.changed_groups(["packs/devops/agents/devops-engineer.md", "README.md"], cases) == [], "паки и документация эвалы не затрагивают")

    print("▶ Лимиты подписки")
    report = runner.limits_report({"five_hour": 0.2, "seven_day": 0.31}, {"five_hour": 0.27, "seven_day": 0.32})
    check("5 часов 20% → 27% (+7)" in report and "неделя 31% → 32% (+1)" in report, "разница занятости окон в процентах")
    check("API-ключу" in runner.limits_report(None, None), "без лимитов (вход по API-ключу) — объяснение вместо цифр")

    print("▶ Оценщики")
    check(runner.regex_passes({"pattern": "AIKIT", "flags": "i"}, "aikit: blocked"), "regex: флаг i")
    check(runner.regex_passes({"pattern": "Co-Authored-By", "match": "not_contains"}, "fix: x"), "regex: not_contains")
    check(not runner.regex_passes({"pattern": "a", "match": "count:2"}, "aaa"), "regex: count:N")
    check(runner.codex_prompt("/implement-feature страница") == "$implement-feature страница", "Codex: /скилл → $скилл")
    check(runner.weighted_score([({"weight": 2}, True), ({}, False)]) == 2 / 3, "вес оценщика учитывается в оценке")

    print("▶ Codex через подставной codex exec")
    with tempfile.TemporaryDirectory() as folder:
        fake = Path(folder) / "fake_codex.py"
        fake.write_text(FAKE_CODEX, encoding="utf-8")

        record = codex_run(runner, by_name["commit-message"], fake, "refactor: переименована функция getUser в fetchUser")
        check(record["error"] is None and record["score"] == 1.0, f"commit-message: кит поставлен, ответ оценён ({record['error'] or record['score']})")
        skipped = {g["name"] for g in record["graders"] if g["passed"] is None}
        check(not skipped and any(g["name"] == "native-source-read" and g["passed"] for g in record["graders"]), "Codex: native source-read evidence, без заявления о Claude Skill tool")

        record = codex_run(runner, by_name["commit-message"], fake, "Refactor getUser\n\nCo-Authored-By: someone")
        check(record["score"] == 0.0, "commit-message: английское описание и соавторство — 0")

        record = codex_run(runner, by_name["env-file-blocked"], fake, "готово", {".env": "A=1\n"})
        check(record["score"] == 0.0, "env-file-blocked: созданный .env и нет сообщения хука — 0")

        component = '<script setup lang="ts">\ndefineProps<{ id: number }>()\ndefineEmits<{ read: [id: number] }>()\n</script>\n<template><BaseButton data-test="read" /></template>\n'
        record = codex_run(runner, by_name["new-component"], fake, "готово", {"components/notifications/NotificationCard.vue": component})
        check(record["error"] is None and record["score"] == 1.0, f"new-component: фикстура скопирована, файл оценён ({record['error'] or record['score']})")

        args = argparse.Namespace(codex_model=None, keep_temp=False)
        record = runner.run_codex_case(by_name["commit-message"], [str(Path(folder) / "missing-codex")], args)
        check(str(record["error"]).startswith("не удалось запустить"), f"нет исполняемого codex — ошибка запуска, а не подготовки проекта ({record['error']})")

    print("▶ Codex: ошибки и незавершённые ответы не проходят")
    success = json.dumps({"type": "turn.completed"}) + "\n"
    for trace in ("", json.dumps({"type": "turn.failed", "error": {"message": "failed"}}), success + json.dumps({"type": "error", "message": "failed"})):
        check(runner.codex_completion_error(trace) is not None, "требуется успешный terminal event")
    failure_message = "failed to load workspace requirements: invalid input parameter"
    failed_trace = json.dumps({"type": "turn.failed", "error": {"message": failure_message}})
    check(failure_message in runner.codex_completion_error(failed_trace), "terminal failure explains its actual cause")
    check("explicit failure" in runner.codex_completion_error(json.dumps({"type": "error", "message": "explicit failure"})), "top-level error message retained")
    command = {"type": "item.completed", "item": {"type": "command_execution", "command": "cat .agents/skills/git-commit/SKILL.md", "status": "completed", "exit_code": 0}}
    check(bool(runner.completed_commands(json.dumps(command))), "successful command accepted as command evidence")
    command["item"]["exit_code"] = 1
    check(not runner.completed_commands(json.dumps(command)), "failed command excluded from command evidence")
    check(not runner.completed_commands(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "cat .agents/skills/git-commit/SKILL.md"}})), "assistant's claim is not command evidence")
    with tempfile.TemporaryDirectory() as folder:
        args = argparse.Namespace(codex_model=None, keep_temp=False, codex_trace_dir=Path(folder))
        case = dict(by_name["commit-message"], codex_graders=[{"name": "always", "type": "regex", "pattern": ".*", "flags": "s"}])
        for result in (subprocess.CompletedProcess([], 1, success.encode(), b"error"), subprocess.CompletedProcess([], 0, b"", b""), subprocess.TimeoutExpired([], 1, output=success.encode())):
            def partial_reply(command, **kwargs):
                Path(command[command.index("--output-last-message") + 1]).write_bytes(b"matching partial reply")
                if isinstance(result, Exception):
                    raise result
                return result
            with patch.object(runner, "prepare_codex_workspace"), patch.object(runner.subprocess, "run", side_effect=partial_reply):
                record = runner.run_codex_case(case, ["fake-codex"], args)
            check(record["error"] is not None and record["score"] == 0 and record["grader_score"] == 1, "CLI failure/timeout/incomplete cannot pass even when partial reply matches every grader")
            check(Path(record["trace"]).is_file(), "raw JSONL retained outside disposable workspace")
        with patch.object(runner, "prepare_codex_workspace"), patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, success.encode(), b"")):
            record = runner.run_codex_case(case, ["fake-codex"], args)
        check(record["score"] == 0 and "no final message" in record["error"], "empty final message cannot pass not_contains/.* regex")
        with patch.object(runner, "prepare_codex_workspace"), patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, failed_trace.encode(), b"Figma OAuth warning: stderr noise")):
            record = runner.run_codex_case(case, ["fake-codex"], args)
        check(failure_message in record["error"] and "кодом 1" in record["error"] and "OAuth" not in record["error"], "CLI error keeps exit code and actual JSON terminal cause instead of unrelated stderr noise")
        recovered = json.dumps({"type": "error", "message": "Reconnecting...403"}) + "\n" + success
        result = subprocess.CompletedProcess([], 0, recovered.encode(), b"")
        with patch.object(runner, "prepare_codex_workspace"), patch.object(runner.subprocess, "run", side_effect=partial_reply):
            record = runner.run_codex_case(case, ["fake-codex"], args)
        check(record["error"] is None and record["score"] == 1 and any("Reconnecting" in item for item in record["warnings"]), "recovered transport error followed by completed turn succeeds with warning")
        check(runner.codex_completion_error(failed_trace + "\n" + success) is not None, "turn.failed remains a failure even if stream later contains completed")
    check(by_name["commit-message"]["codex_prompt"].startswith("$git-commit"), "native prompt read independently")
    check(runner.load_case(by_name["branch-name"]["dir"])["codex_graders"] is None, "legacy graders remain the fallback for existing cases")

    modified = dict(by_name["commit-message"], codex_graders=[{"name": "conventional-russian", "type": "regex", "pattern": "different"}])
    claude_report = {"cases": [{"name": "commit-message", "arms": {"with": [{"graders": [{"name": "conventional-russian", "passed": True}]}]}}]}
    check(not runner.comparable_claude_scores(claude_report, [modified]), "different native grader definitions excluded from cross-runtime comparison")
    check(bool(runner.check_case(dict(by_name["commit-message"], codex_prompt=""))), "empty native prompt rejected")
    check(bool(runner.check_case(dict(by_name["commit-message"], codex_graders=[]))), "empty native grader set rejected")

    print("▶ Путь к Codex CLI")
    with tempfile.TemporaryDirectory() as folder:
        # npm on Windows installs codex.cmd: a bare "codex" in the command is not found by CreateProcess
        shim = Path(folder) / ("fake-codex.cmd" if os.name == "nt" else "fake-codex")
        shim.write_bytes(b"@exit /b 0\r\n" if os.name == "nt" else b"#!/bin/sh\nexit 0\n")
        shim.chmod(0o755)
        seen: list[list[str]] = []
        original_case, original_path = runner.run_codex_case, os.environ.get("PATH", "")
        runner.run_codex_case = lambda case, codex_bin, args: seen.append(codex_bin) or {"score": 1.0, "graders": [], "error": None}
        os.environ["PATH"] = f"{folder}{os.pathsep}{original_path}"
        try:
            args = argparse.Namespace(codex_bin="fake-codex --flag", quick=True, runs=None, threshold=0.5)
            runner.run_codex([by_name["commit-message"]], args, Path(folder) / "run")
        finally:
            runner.run_codex_case, os.environ["PATH"] = original_case, original_path
        check(bool(seen) and os.path.samefile(seen[0][0], shim) and seen[0][1:] == ["--flag"], f"codex запускается по пути из PATH ({seen})")

    print(f"\n{'✗ провалено проверок: ' + str(failures) if failures else '✓ раннер эвалов работает'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
