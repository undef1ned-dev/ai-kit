#!/usr/bin/env python3
"""
Run the AIKit eval suite (evals/) locally — in Claude Code, in Codex, or in both to compare them.

Every run is a real model call: on a subscription it spends the plan's usage limits, with an API key it is
billed. Nothing runs this automatically — not CI, not hooks. Start it yourself when agents, skills or hooks
changed. Dollar figures are claude plugin eval's API list-price estimate; on a subscription the script also
reports how the 5-hour and weekly limits moved during the run.

Claude Code: `claude plugin eval` loads the core plugin (the repository root) and the profile plugin
of the case, prepares the project with the case's setup.sh and scores the graders.

Codex has no eval command: this script prepares the same project with the Codex adapter installer,
runs `codex exec` and scores the graders that do not depend on Claude Code — regex over the reply,
the trace or a file, and file_exists. tool_used (skills, agents) and judge graders are skipped.

Usage:
    python3 scripts/run-evals.py --list
    python3 scripts/run-evals.py --quick                         # every case once, no baseline
    python3 scripts/run-evals.py vue-nuxt --quick                # only one profile; "all" — every group
    python3 scripts/run-evals.py vue-nuxt core --case 'review-*'
    python3 scripts/run-evals.py --changed --list                # groups touched by the branch and uncommitted changes
    python3 scripts/run-evals.py                                 # 3 runs per case and a no-plugin baseline
    python3 scripts/run-evals.py --runtime both --quick          # Claude Code and Codex side by side
    python3 scripts/run-evals.py --check                         # validate the case files, no model calls
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = ROOT / "evals"
RESULTS_DIR = EVALS_DIR / "results"
SETUP_SCRIPT = EVALS_DIR / "lib" / "setup-project.sh"
CORE_GROUP = "core"
CLAUDE_ONLY_TAG = "claude-only"
# Codex reads skills and agents from the project, so a case without its own setup gets the kit with this profile
CODEX_DEFAULT_PROFILE = "vue-nuxt"
DEFAULT_MODEL = "sonnet"
DEFAULT_JUDGE_MODEL = "haiku"
DEFAULT_MAX_COST_USD = 10.0
DEFAULT_THRESHOLD = 0.8
DEFAULT_TIMEOUT_SECONDS = 300
# claude plugin eval gives a scaffold script the same limit
SETUP_TIMEOUT_SECONDS = 120
# Tools the cases may use beyond the read-only set; Bash is not granted: Windows has no sandbox for it
GRANTED_TOOLS = ["Write", "Edit"]
GRADER_TYPES = {"regex", "tool_used", "tool_order", "file_exists", "llm", "baseline"}
CODEX_GRADER_TYPES = {"regex", "file_exists"}
GRADER_TARGETS = {"last_message", "trace", "files", "mock_calls"}
REGEX_FLAGS = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL, "u": 0}
ALL_GROUPS = "all"
DEFAULT_CHANGED_BASE = "origin/main"
# Changes here reach every case: the core plugin, the hook script and how the eval project is connected
SHARED_PATHS = (
    "base/", "evals/lib/", "adapters/", "scripts/plugin-init.py", "scripts/profile_contract.py",
    "scripts/hooks_config.py", "scripts/install-adapter-package.py", "scripts/build-adapter-package.py",
)
# API list-price estimate of one Claude Code run with sonnet, from the first runs of the suite.
# On a subscription nothing is billed: runs spend the plan's usage limits.
ESTIMATED_RUN_COST_USD = 0.07
FULL_RUNS_PER_CASE = 3 * 2
# A one-word `claude -p` request: its stream reports how much of the subscription limits is used
LIMITS_PROBE_PROMPT = "Ответь одним словом: ок"
LIMITS_PROBE_TIMEOUT_SECONDS = 90
LIMIT_WINDOWS = {"five_hour": "5 часов", "seven_day": "неделя"}
PERCENT = 100


# ---------------------------------------------------------------------------
# Case files: the subset of YAML the suite uses (scalars, inline lists and maps, one nested block)


def split_inline(text: str) -> list[str]:
    """Split `a, "b, c", {d: e}` on top-level commas."""
    items, depth, quote, current = [], 0, "", ""
    for char in text:
        if quote:
            current += char
            if char == quote:
                quote = ""
            continue
        if char in "\"'":
            quote = char
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        elif char == "," and depth == 0:
            items.append(current.strip())
            current = ""
            continue
        current += char
    if current.strip():
        items.append(current.strip())
    return items


def parse_scalar(text: str):
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        return [parse_scalar(item) for item in split_inline(text[1:-1])]
    if text.startswith("{") and text.endswith("}"):
        return dict(split_key(item) for item in split_inline(text[1:-1]))
    if len(text) >= 2 and text[0] == text[-1] == "'":
        return text[1:-1].replace("''", "'")
    if len(text) >= 2 and text[0] == text[-1] == '"':
        return json.loads(text)
    if text in {"true", "false"}:
        return text == "true"
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def split_key(line: str) -> tuple[str, object]:
    key, _, value = line.partition(":")
    return key.strip(), parse_scalar(value)


def parse_yaml(text: str) -> dict:
    data: dict = {}
    block: dict | None = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith((" ", "\t")):
            if block is None:
                raise ValueError(f"отступ без родительского ключа: {raw.strip()}")
            key, value = split_key(raw.strip())
            block[key] = value
            continue
        key, _, value = raw.partition(":")
        if value.strip():
            data[key.strip()] = parse_scalar(value)
            block = None
        else:
            block = data.setdefault(key.strip(), {})
    return data


def read_front_matter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.DOTALL)
    if not match:
        return {}, text.strip()
    return parse_yaml(match.group(1)), match.group(2).strip()


def load_case(case_dir: Path) -> dict:
    meta: dict = {}
    yaml_path = case_dir / "case.yaml"
    if yaml_path.exists():
        meta = parse_yaml(yaml_path.read_text(encoding="utf-8"))
        meta.update(meta.pop("execution", {}) if isinstance(meta.get("execution"), dict) else {})
    prompt_path = case_dir / "prompt.md"
    prompt = meta.get("prompt", "")
    if prompt_path.exists():
        front, prompt = read_front_matter(prompt_path)
        meta.update(front)
    graders = []
    for path in sorted((case_dir / "graders").glob("*.md")):
        front, body = read_front_matter(path)
        grader = {"name": path.stem, **front}
        if body:
            grader.setdefault("criteria" if grader.get("type") in {"llm", "baseline"} else "pattern", body)
        graders.append(grader)
    group = case_dir.relative_to(EVALS_DIR).parts[0]
    return {
        "dir": case_dir,
        "name": meta.get("name") or case_dir.name,
        "group": group,
        "tags": meta.get("tags") or [],
        "prompt": prompt,
        "timeout": int(meta.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS),
        "plugins": meta.get("plugins") or [],
        "scaffold": (meta.get("context") or {}).get("scaffold_script"),
        "graders": graders,
    }


def discover_cases() -> list[dict]:
    dirs = sorted(
        {path.parent for name in ("prompt.md", "case.yaml") for path in EVALS_DIR.rglob(name)},
        key=lambda path: path.as_posix(),
    )
    return [load_case(path) for path in dirs if RESULTS_DIR not in path.parents]


def select_cases(cases: list[dict], profiles: list[str], case_glob: str | None) -> list[dict]:
    selected = [case for case in cases if not profiles or set(case["tags"]) & set(profiles)]
    if case_glob:
        selected = [case for case in selected if fnmatch.fnmatch(case["name"], case_glob)]
    return selected


# ---------------------------------------------------------------------------
# --check: the suite loads, regexes compile, setup scripts point to real profiles and fixtures


def setup_arguments(script: Path) -> list[str]:
    for line in script.read_text(encoding="utf-8").splitlines():
        if "setup-project.sh" in line and line.lstrip().startswith("bash "):
            return shlex.split(line.split('setup-project.sh"', 1)[1])
    return []


def check_case(case: dict) -> list[str]:
    where = case["dir"].relative_to(ROOT).as_posix()
    problems = []
    if not case["prompt"]:
        problems.append(f"{where}: пустой промпт")
    if not case["graders"]:
        problems.append(f"{where}: нет ни одного оценщика в graders/")
    if case["group"] not in case["tags"]:
        problems.append(f"{where}: в tags нет группы «{case['group']}» — по ней фильтрует --profile")
    if case["group"] != CORE_GROUP and not (ROOT / "profiles" / case["group"]).is_dir():
        problems.append(f"{where}: группа «{case['group']}» — не профиль кита")
    for plugin in case["plugins"]:
        if not (case["dir"] / plugin / ".claude-plugin" / "plugin.json").exists():
            problems.append(f"{where}: plugins → {plugin} — не плагин")
    if case["scaffold"]:
        script = case["dir"] / case["scaffold"]
        if not script.exists():
            problems.append(f"{where}: нет скрипта подготовки {case['scaffold']}")
        else:
            arguments = setup_arguments(script)
            if not arguments:
                problems.append(f"{where}: {case['scaffold']} не вызывает evals/lib/setup-project.sh")
            for profile in arguments[:1][0].split("+") if arguments else []:
                if not (ROOT / "profiles" / profile).is_dir():
                    problems.append(f"{where}: {case['scaffold']} — нет профиля {profile}")
            if len(arguments) > 1 and not (EVALS_DIR / "fixtures" / arguments[1]).is_dir():
                problems.append(f"{where}: {case['scaffold']} — нет фикстуры evals/fixtures/{arguments[1]}")
    for grader in case["graders"]:
        label = f"{where}/graders/{grader['name']}.md"
        kind = grader.get("type")
        if kind not in GRADER_TYPES:
            problems.append(f"{label}: неизвестный type «{kind}»")
            continue
        if kind == "regex":
            try:
                re.compile(grader.get("pattern", ""), regex_flags(grader))
            except re.error as error:
                problems.append(f"{label}: регулярка не компилируется: {error}")
            target = grader.get("target", "last_message")
            file_target = isinstance(target, dict) and target.get("source") == "file" and target.get("path")
            if not (file_target or isinstance(target, str) and target in GRADER_TARGETS):
                problems.append(f"{label}: неизвестный target {target}")
        if kind == "tool_used" and not grader.get("tool"):
            problems.append(f"{label}: нет tool")
        if kind == "file_exists" and not grader.get("path"):
            problems.append(f"{label}: нет path")
    return problems


def run_check(cases: list[dict]) -> int:
    problems = [problem for case in cases for problem in check_case(case)]
    names = [case["name"] for case in cases]
    problems += [f"имя кейса «{name}» повторяется — --case и отчёт его не различат" for name in sorted({n for n in names if names.count(n) > 1})]
    for problem in problems:
        print(f"  ✗ {problem}", file=sys.stderr)
    if not problems:
        print(f"  ✓ кейсов: {len(cases)}, оценщиков: {sum(len(case['graders']) for case in cases)}")
    return 1 if problems else 0


def print_list(cases: list[dict]) -> None:
    for case in cases:
        runtimes = "Claude Code" if CLAUDE_ONLY_TAG in case["tags"] else "Claude Code, Codex"
        print(f"{case['group']:<16} {case['name']:<22} оценщиков: {len(case['graders'])}  ({runtimes})")
    groups = sorted({case["group"] for case in cases}, key=lambda group: (group != CORE_GROUP, group))
    quick = len(cases) * ESTIMATED_RUN_COST_USD
    print(f"\nГруппы: {', '.join(groups)} · кейсов: {len(cases)}")
    print(
        f"Объём в Claude Code по прайсу API: --quick ≈ ${quick:.2f}, полный прогон ≈ ${quick * FULL_RUNS_PER_CASE:.2f}. "
        "На подписке деньги не списываются — тратятся лимиты; сколько, раннер покажет после прогона"
    )


def known_groups(cases: list[dict]) -> list[str]:
    return sorted({case["group"] for case in cases}, key=lambda group: (group != CORE_GROUP, group))


def resolve_groups(requested: list[str], cases: list[dict]) -> list[str] | None:
    """Group names from the command line; [] means every group. None — a name is unknown (reported)."""
    if ALL_GROUPS in requested:
        return []
    known = known_groups(cases)
    unknown = [group for group in requested if group not in known]
    for group in unknown:
        hint = "у профиля пока нет кейсов в evals/" if (ROOT / "profiles" / group).is_dir() else "нет такой группы"
        print(f"✗ {group}: {hint}. Группы: {', '.join(known)} или {ALL_GROUPS}", file=sys.stderr)
    return None if unknown else list(dict.fromkeys(requested))


def git_lines(*command: str) -> list[str]:
    result = subprocess.run(["git", *command], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()] if result.returncode == 0 else []


def changed_files(base: str) -> list[str]:
    """Files changed on the branch since it left base, plus uncommitted and untracked ones."""
    committed = git_lines("diff", "--name-only", f"{base}...HEAD")
    uncommitted = git_lines("status", "--porcelain", "--untracked-files=all")
    return sorted(set(committed) | {line[3:].split(" -> ")[-1].strip('"') for line in uncommitted})


def fixture_groups(cases: list[dict]) -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {}
    for case in cases:
        script = case["dir"] / case["scaffold"] if case["scaffold"] else None
        arguments = setup_arguments(script) if script and script.exists() else []
        if len(arguments) > 1:
            groups.setdefault(arguments[1], set()).add(case["group"])
    return groups


def changed_groups(files: list[str], cases: list[dict]) -> list[str]:
    """Groups whose cases a change can affect: a profile, its cases or fixture; base and the setup reach every group."""
    known = set(known_groups(cases))
    by_fixture = fixture_groups(cases)
    groups: set[str] = set()
    for path in files:
        parts = path.split("/")
        if path.startswith(SHARED_PATHS):
            return known_groups(cases)
        if parts[0] == "profiles" and len(parts) > 1 and parts[1] in known:
            groups.add(parts[1])
        elif parts[0] == "evals" and len(parts) > 2 and parts[1] == "fixtures":
            groups |= by_fixture.get(parts[2], set())
        elif parts[0] == "evals" and len(parts) > 1 and parts[1] in known:
            groups.add(parts[1])
    return [group for group in known_groups(cases) if group in groups]


# ---------------------------------------------------------------------------
# Claude Code: claude plugin eval


def python3_shim() -> Path | None:
    """
    On Windows `python3` is often the Python Install Manager alias, which looks for runtimes in the
    user profile. Eval runs get a temporary HOME, the alias finds nothing and the plugin hooks fail.
    A `python3` script ahead on PATH points the hooks straight at this interpreter.
    """
    if os.name != "nt":
        return None
    folder = Path(tempfile.mkdtemp(prefix="aikit-evals-python3-"))
    interpreter = Path(sys.executable).as_posix()
    (folder / "python3").write_text(f'#!/bin/sh\nexec "{interpreter}" "$@"\n', encoding="utf-8", newline="\n")
    return folder


def claude_executable() -> str:
    """
    The resolved path: an npm install on Windows puts claude.cmd on PATH, and CreateProcess runs
    only .exe for a bare "claude" (WinError 2). Same for codex in run_codex.
    """
    return shutil.which("claude") or "claude"


def claude_command(args: argparse.Namespace, output_dir: Path) -> list[str]:
    command = [
        claude_executable(), "plugin", "eval", ".",
        "--scaffold", "--trust-plugin", "--no-publish",
        "--model", args.model, "--judge-model", args.judge_model,
        "--threshold", str(args.threshold), "--max-cost-usd", str(args.max_cost_usd),
        "--output-dir", str(output_dir),
    ]
    if args.runs:
        command += ["--runs", str(args.runs)]
    if args.quick:
        command += ["--runs", "1", "--ablation", "none"]
    if args.concurrency:
        command += ["--concurrency", str(args.concurrency)]
    if args.case:
        command += ["--case", args.case]
    if args.profile:
        command += ["--tag", *args.profile]
    return command + ["--allow-tools", *GRANTED_TOOLS]


def subscription_limits() -> dict[str, float] | None:
    """
    Share of each subscription limit window in use (0..1), from the rate_limit_event of a tiny
    `claude -p` request. None with API-key auth or when the event is missing.
    """
    command = [
        claude_executable(), "-p", LIMITS_PROBE_PROMPT, "--model", DEFAULT_JUDGE_MODEL,
        "--output-format", "stream-json", "--verbose", "--max-turns", "1", "--tools", "",
    ]
    with tempfile.TemporaryDirectory(prefix="aikit-evals-limits-") as folder:
        try:
            completed = subprocess.run(command, cwd=folder, capture_output=True, timeout=LIMITS_PROBE_TIMEOUT_SECONDS)
        except (OSError, subprocess.SubprocessError):
            return None
    for line in completed.stdout.decode("utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        windows = (event.get("rate_limit_info") or {}).get("unifiedWindows") if event.get("type") == "rate_limit_event" else None
        if windows:
            return {name: float(window["utilization"]) for name, window in windows.items() if name in LIMIT_WINDOWS and "utilization" in window}
    return None


def limits_report(before: dict[str, float] | None, after: dict[str, float] | None) -> str:
    if not before or not after:
        return (
            "Лимиты подписки не видны — похоже, вход по API-ключу: тогда прогон оплачивается по прайсу, "
            "оценка — в столбце COST выше"
        )
    parts = []
    for name, label in LIMIT_WINDOWS.items():
        if name in before and name in after:
            start, end = round(before[name] * PERCENT), round(after[name] * PERCENT)
            delta = end - start
            parts.append(f"{label} {start}% → {end}% ({'+' if delta >= 0 else ''}{delta})")
    return (
        "Лимиты подписки: " + ", ".join(parts)
        + ". Это занятость всего аккаунта: другие сессии в это время тоже в ней. Меньше 1% не видно"
    )


def run_claude(args: argparse.Namespace, run_dir: Path) -> tuple[int, dict | None]:
    if not shutil.which("claude"):
        print("✗ claude не найден в PATH", file=sys.stderr)
        return 1, None
    output_dir = run_dir / "claude"
    env = dict(os.environ)
    shim = python3_shim()
    if shim:
        env["PATH"] = f"{shim}{os.pathsep}{env.get('PATH', '')}"
    if os.name == "nt":
        bash_dir = Path(bash_executable()).parent
        if bash_dir.is_dir():
            env["PATH"] = f"{bash_dir}{os.pathsep}{env.get('PATH', '')}"
    command = claude_command(args, output_dir)
    limits_before = None if args.no_limits else subscription_limits()
    print("▶ Claude Code:", " ".join(shlex.quote(part) for part in command), flush=True)
    try:
        code = subprocess.run(command, cwd=ROOT, env=env).returncode
    finally:
        if shim:
            shutil.rmtree(shim, ignore_errors=True)
    if not args.no_limits:
        limits_after = subscription_limits()
        print("\n" + limits_report(limits_before, limits_after))
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "limits.json").write_text(
            json.dumps({"before": limits_before, "after": limits_after}, indent=2) + "\n", encoding="utf-8",
        )
    result_path = output_dir / "aggregate-result.json"
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else None
    return code, result


# ---------------------------------------------------------------------------
# Codex: codex exec and the graders that do not depend on Claude Code


def codex_prompt(prompt: str) -> str:
    """Skills are invoked as $name in Codex, as /name in Claude Code."""
    return re.sub(r"^/([\w-]+)", r"$\1", prompt)


def workspace_files(workspace: Path) -> set[str]:
    return {path.relative_to(workspace).as_posix() for path in workspace.rglob("*") if path.is_file()}


def bash_executable() -> str:
    """
    A bare "bash" on Windows resolves to System32\bash.exe (WSL) before PATH is searched:
    take the Git Bash that ships with git.
    """
    if os.name == "nt":
        git = shutil.which("git")
        if git:
            for candidate in (Path(git).parents[1] / "bin" / "bash.exe", Path(git).parents[1] / "usr" / "bin" / "bash.exe"):
                if candidate.exists():
                    return str(candidate)
    return shutil.which("bash") or "bash"


def prepare_codex_workspace(case: dict, workspace: Path) -> None:
    env = {**os.environ, "AIKIT_EVAL_RUNTIME": "codex"}
    if case["scaffold"]:
        command = [bash_executable(), (case["dir"] / case["scaffold"]).as_posix()]
    else:
        command = [bash_executable(), SETUP_SCRIPT.as_posix(), CODEX_DEFAULT_PROFILE]
    result = subprocess.run(command, cwd=workspace, env=env, capture_output=True, timeout=SETUP_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise OSError(result.stderr.decode("utf-8", errors="replace").strip()[-500:] or f"exit {result.returncode}")


def codex_command(codex_bin: list[str], args: argparse.Namespace, workspace: Path, last_message: Path, prompt: str) -> list[str]:
    trusted = f"projects.{json.dumps(str(workspace))}.trust_level=\"trusted\""
    command = [
        *codex_bin, "exec", "--json", "--skip-git-repo-check",
        "--sandbox", "workspace-write", "--cd", str(workspace),
        "--output-last-message", str(last_message), "-c", trusted,
    ]
    if args.codex_model:
        command += ["--model", args.codex_model]
    return command + [prompt]


def regex_flags(grader: dict) -> int:
    flags = 0
    for letter in str(grader.get("flags", "")):
        flags |= REGEX_FLAGS.get(letter, 0)
    return flags


def regex_passes(grader: dict, text: str) -> bool:
    found = re.findall(grader.get("pattern", ""), text, regex_flags(grader))
    mode = str(grader.get("match", "contains"))
    if mode == "not_contains":
        return not found
    if mode.startswith("count:"):
        return len(found) == int(mode.split(":", 1)[1])
    return bool(found)


def grade_codex(grader: dict, workspace: Path, created: list[str], reply: str, trace: str) -> bool | None:
    kind = grader.get("type")
    if kind == "file_exists":
        exists = any(fnmatch.fnmatch(path, grader["path"]) for path in created)
        return exists == bool(grader.get("exists", True))
    if kind != "regex":
        return None
    target = grader.get("target", "last_message")
    if isinstance(target, dict):
        path = workspace / target["path"]
        text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    else:
        text = {"last_message": reply, "trace": trace, "files": "\n".join(created)}.get(target)
        if text is None:
            return None
    return regex_passes(grader, text)


def weighted_score(results: list[tuple[dict, bool]]) -> float | None:
    total = sum(float(grader.get("weight", 1)) for grader, _ in results)
    if not total:
        return None
    return sum(float(grader.get("weight", 1)) for grader, passed in results if passed) / total


def run_codex_case(case: dict, codex_bin: list[str], args: argparse.Namespace) -> dict:
    workspace = Path(tempfile.mkdtemp(prefix=f"aikit-eval-{case['name']}-"))
    last_message = workspace.parent / f"{workspace.name}-last-message.txt"
    record: dict = {"name": case["name"], "group": case["group"], "graders": [], "error": None}
    stage = "подготовка проекта не удалась"
    try:
        prepare_codex_workspace(case, workspace)
        before = workspace_files(workspace)
        command = codex_command(codex_bin, args, workspace, last_message, codex_prompt(case["prompt"]))
        stage = f"не удалось запустить {codex_bin[0]}"
        try:
            completed = subprocess.run(command, capture_output=True, timeout=case["timeout"])
            trace = completed.stdout.decode("utf-8", errors="replace")
            if completed.returncode != 0:
                record["error"] = f"codex exec завершился с кодом {completed.returncode}: {completed.stderr.decode('utf-8', errors='replace')[-500:]}"
        except subprocess.TimeoutExpired as expired:
            trace = (expired.stdout or b"").decode("utf-8", errors="replace")
            record["error"] = f"timed out after {case['timeout']}s"
        stage = "оценка ответа не удалась"
        reply = last_message.read_text(encoding="utf-8", errors="replace") if last_message.exists() else ""
        created = sorted(workspace_files(workspace) - before)
        scored = []
        for grader in case["graders"]:
            passed = grade_codex(grader, workspace, created, reply, trace)
            record["graders"].append({"name": grader["name"], "type": grader.get("type"), "passed": passed})
            if passed is not None:
                scored.append((grader, passed))
        record["score"] = weighted_score(scored)
    except (OSError, subprocess.SubprocessError) as error:
        record["error"] = f"{stage}: {error}"
        record["score"] = 0.0
    finally:
        if args.keep_temp:
            record["workspace"] = str(workspace)
        else:
            shutil.rmtree(workspace, ignore_errors=True)
        last_message.unlink(missing_ok=True)
    return record


def run_codex(cases: list[dict], args: argparse.Namespace, run_dir: Path) -> tuple[int, list[dict]]:
    codex_bin = shlex.split(args.codex_bin, posix=os.name != "nt")
    resolved = shutil.which(codex_bin[0])
    if not resolved:
        print(f"✗ {codex_bin[0]} не найден в PATH — поставь Codex CLI", file=sys.stderr)
        return 1, []
    codex_bin = [resolved, *codex_bin[1:]]
    runs = 1 if args.quick else (args.runs or 1)
    records = []
    for case in cases:
        if CLAUDE_ONLY_TAG in case["tags"]:
            continue
        for number in range(1, runs + 1):
            record = run_codex_case(case, codex_bin, args)
            record["run"] = number
            records.append(record)
            score = "—" if record["score"] is None else f"{record['score']:.2f}"
            marks = " ".join(f"{'✓' if g['passed'] else '✗'} {g['name']}" for g in record["graders"] if g["passed"] is not None)
            print(f"  Codex {case['name']} run {number}/{runs}: {score}  {marks}" + (f"  ⚠ {record['error']}" if record["error"] else ""), flush=True)
    output = run_dir / "codex.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"runs": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failed = any(record["error"] or (record["score"] is not None and record["score"] < args.threshold) for record in records)
    return (1 if failed else 0), records


# ---------------------------------------------------------------------------
# Summary


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def comparable_claude_scores(result: dict, cases: list[dict]) -> dict[str, float]:
    """Claude Code with-arm score over the graders Codex can score too, so the columns compare the same checks."""
    types = {case["name"]: {g["name"]: g for g in case["graders"]} for case in cases}
    scores = {}
    for case in result.get("cases", []):
        graders = types.get(case.get("name"), {})
        per_run = []
        for run in case.get("arms", {}).get("with", []):
            results = [
                (graders[item["name"]], bool(item.get("passed")))
                for item in run.get("graders", [])
                if graders.get(item.get("name"), {}).get("type") in CODEX_GRADER_TYPES
            ]
            score = weighted_score(results)
            if score is not None:
                per_run.append(score)
        if per_run:
            scores[case["name"]] = mean(per_run)
    return scores


def print_comparison(cases: list[dict], claude: dict | None, codex: list[dict]) -> None:
    claude_scores = comparable_claude_scores(claude, cases) if claude else {}
    print("\nСравнение по общим проверкам (регулярки и файлы; навыки, агенты и судья не входят)")
    print(f"{'КЕЙС':<24} {'CLAUDE CODE':>11} {'CODEX':>7}")
    for case in cases:
        codex_runs = [r["score"] for r in codex if r["name"] == case["name"] and r["score"] is not None]
        left = claude_scores.get(case["name"])
        right = mean(codex_runs)
        print(f"{case['name']:<24} {'—' if left is None else f'{left:.2f}':>11} {'—' if right is None else f'{right:.2f}':>7}")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Run the AIKit eval suite locally")
    parser.add_argument("--runtime", choices=["claude", "codex", "both"], default="claude")
    parser.add_argument("groups", nargs="*", help=f"groups to run: core, a profile name or {ALL_GROUPS} (default: {ALL_GROUPS})")
    parser.add_argument("--profile", action="append", default=[], help="same as a positional group; repeatable")
    parser.add_argument(
        "--changed", nargs="?", const=DEFAULT_CHANGED_BASE, metavar="BASE",
        help=f"only the groups touched since BASE (default {DEFAULT_CHANGED_BASE}) and by uncommitted changes",
    )
    parser.add_argument("--case", help="case name glob, e.g. 'review-*'")
    parser.add_argument("--quick", action="store_true", help="one run per case, no no-plugin baseline")
    parser.add_argument("--runs", type=int, help="runs per case (Claude Code default: 3)")
    parser.add_argument("-j", "--concurrency", type=int, help="Claude Code runs at once (1-8)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Claude Code model under test")
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    parser.add_argument("--codex-model", help="Codex model (default: Codex config)")
    parser.add_argument("--codex-bin", default="codex", help="Codex CLI command")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument(
        "--max-cost-usd", type=float, default=DEFAULT_MAX_COST_USD,
        help="ceiling on the API list-price estimate of the Claude Code runs; on a subscription it caps limit use",
    )
    parser.add_argument("--no-limits", action="store_true", help="do not measure subscription limits before and after")
    parser.add_argument("--keep-temp", action="store_true", help="keep Codex workspaces for debugging")
    parser.add_argument("--list", action="store_true", help="list the cases and exit")
    parser.add_argument("--check", action="store_true", help="validate the case files, no model calls")
    args = parser.parse_args()

    cases = discover_cases()
    if args.check:
        return run_check(cases)
    groups = resolve_groups(args.groups + args.profile, cases)
    if groups is None:
        return 1
    if args.changed:
        touched = changed_groups(changed_files(args.changed), cases)
        if not touched:
            print(f"Изменения с {args.changed} не затрагивают ни профили, ни base — эвалы гонять незачем")
            return 0
        print(f"Затронуты изменениями с {args.changed}: {', '.join(touched)}")
        groups = [group for group in touched if not groups or group in groups]
    args.profile = groups
    selected = select_cases(cases, groups, args.case)
    if args.list:
        print_list(selected)
        return 0
    if not selected:
        print("✗ под фильтры не подошёл ни один кейс — см. --list", file=sys.stderr)
        return 1

    run_dir = RESULTS_DIR / datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    codes = []
    claude_result = None
    codex_records: list[dict] = []
    if args.runtime in {"claude", "both"}:
        code, claude_result = run_claude(args, run_dir)
        codes.append(code)
    if args.runtime in {"codex", "both"}:
        print("▶ Codex", flush=True)
        code, codex_records = run_codex(selected, args, run_dir)
        codes.append(code)
    if args.runtime == "both":
        print_comparison(selected, claude_result, codex_records)
    print(f"\nРезультаты: {run_dir.relative_to(ROOT).as_posix()}/")
    return max(codes)


if __name__ == "__main__":
    raise SystemExit(main())
