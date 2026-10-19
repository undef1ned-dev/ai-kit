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
    check(runner.changed_groups(["evals/fixtures/fastapi-app/routers/users.py"], cases) == ["python-fastapi"], "правка фикстуры — группы, которые её используют")
    check(runner.changed_groups(["evals/python-django/new-app/prompt.md"], cases) == ["python-django"], "правка кейса — его группа")
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
        check(skipped == {"skill-fired"}, "tool_used: Skill в Codex не оценивается")

        record = codex_run(runner, by_name["commit-message"], fake, "Refactor getUser\n\nCo-Authored-By: someone")
        check(record["score"] == 0.0, "commit-message: английское описание и соавторство — 0")

        record = codex_run(runner, by_name["env-file-blocked"], fake, "готово", {".env": "A=1\n"})
        check(record["score"] == 0.0, "env-file-blocked: созданный .env и нет сообщения хука — 0")

        component = '<script setup lang="ts">\ndefineProps<{ id: number }>()\ndefineEmits<{ read: [id: number] }>()\n</script>\n<template><BaseButton data-test="read" /></template>\n'
        record = codex_run(runner, by_name["new-component"], fake, "готово", {"components/notifications/NotificationCard.vue": component})
        check(record["error"] is None and record["score"] == 1.0, f"new-component: фикстура скопирована, файл оценён ({record['error'] or record['score']})")

    print(f"\n{'✗ провалено проверок: ' + str(failures) if failures else '✓ раннер эвалов работает'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
