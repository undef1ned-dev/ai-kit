#!/usr/bin/env python3
"""
AIKit hooks: one script for every runtime.

Claude Code and Codex call it directly (hooks in .claude/settings.json and .codex/hooks.json),
OpenCode calls it from the .opencode/plugins/aikit-hooks.js plugin. The event arrives as JSON
on stdin in the Claude Code / Codex shape:

    {"hook_event_name": "PreToolUse", "session_id": "...", "cwd": "...",
     "tool_name": "Bash" | "Write" | "Edit" | "MultiEdit" | "apply_patch", "tool_input": {...}}

Events:
    PreToolUse   — blocks .env writes, secrets in written text, git add of .env files,
                   commit messages outside Conventional Commits or with co-authorship,
                   branch names outside Conventional Branch. Blocking = exit 2, reason on stderr.
    PostToolUse  — runs the profile's format and lint commands from .aikit/profiles.json on the
                   changed file; lint problems go back to the agent as additionalContext.
    Stop         — once code changed, runs the profile's test command; failed tests keep the agent
                   working (decision: block). After a large task suggests /capture-memory,
                   if the project keeps team memory (.aikit/memory/).
    SessionStart — adds .aikit/memory/INDEX.md and PRODUCT.md to the session context. In the plugin
                   (--plugin) also tells the user once per version that a newer AIKit is out: the hook
                   only reads a cache; once a day a detached `--refresh-update-cache` run fetches VERSION
                   from main into it. Off with AIKIT_NO_UPDATE_CHECK=1 or "update_check": false in
                   .aikit/settings.json.

With --plugin (hooks shipped in the AIKit plugin) the hook only acts in projects connected to the kit:
a folder with .aikit/ above the session cwd. Other projects of the user are left alone.
With --deny-json (Codex hooks on Windows) PreToolUse blocks with permissionDecision: deny and exit 0.

The hook never breaks the session: any internal error lets the action through.
Standard library only, Python 3.9+.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

BLOCK_EXIT_CODE = 2
PLUGIN_FLAG = "--plugin"
# Codex on Windows runs hooks through powershell -Command, and Windows PowerShell 5.1 turns exit code 2
# into 1: the block would read as a failed hook. With this flag PreToolUse denies with JSON and exit 0
DENY_JSON_FLAG = "--deny-json"
PROFILES_FILE = Path(".aikit") / "profiles.json"
WORKTREES_DIR = Path(".aikit") / "worktrees"
MEMORY_DIR = Path(".aikit") / "memory"
MEMORY_INDEX = MEMORY_DIR / "INDEX.md"
PRODUCT_FILE = Path("PRODUCT.md")
PRODUCT_TEMPLATE_MARKER = "[Название продукта]"
CONTEXT_FILE_LIMIT = 4000
OUTPUT_TAIL_LINES = 30
FORMAT_TIMEOUT_SECONDS = 60
LINT_TIMEOUT_SECONDS = 90
TEST_TIMEOUT_SECONDS = 480
LARGE_TASK_FILES = 8

# Update notice of the plugin: the root of the core plugin is two folders above this script
PLUGIN_ROOT = Path(__file__).resolve().parents[2]
REFRESH_UPDATE_FLAG = "--refresh-update-cache"
UPDATE_URL = "https://raw.githubusercontent.com/undef1ned-dev/ai-kit/main/VERSION"
UPDATE_URL_ENV = "AIKIT_UPDATE_URL"
UPDATE_CACHE_ENV = "AIKIT_UPDATE_CACHE"
NO_UPDATE_CHECK_ENV = "AIKIT_NO_UPDATE_CHECK"
UPDATE_CHECK_INTERVAL = datetime.timedelta(days=1)
UPDATE_TIMEOUT_SECONDS = 3
UPDATE_RESPONSE_LIMIT = 64
SETTINGS_FILE = Path(".aikit") / "settings.json"
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

ENV_TEMPLATE_SUFFIXES = {"example", "sample", "template", "dist", "defaults"}
SECRET_PATTERNS = {
    "приватный ключ": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----",
    "ключ AWS": r"\bAKIA[0-9A-Z]{16}\b",
    "токен GitHub": r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})\b",
    "токен GitLab": r"\bglpat-[A-Za-z0-9_-]{20,}\b",
    "токен Slack": r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b",
    "ключ Anthropic": r"\bsk-ant-[A-Za-z0-9_-]{20,}",
    "ключ OpenAI": r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}",
    "ключ Google API": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "ключ Stripe": r"\b[sr]k_live_[0-9A-Za-z]{24,}\b",
}
COMMIT_TYPES = "feat|fix|refactor|perf|style|test|docs|build|ci|chore|revert"
COMMIT_SUBJECT = re.compile(rf"^(?:{COMMIT_TYPES})(?:\([^()\s][^()]*\))?!?: \S")
COMMIT_EXEMPT = re.compile(r"^(?:Merge |Revert \"|fixup! |squash! |amend! )")
CO_AUTHORSHIP = re.compile(r"(?im)^\s*co-authored-by:|generated with")
CO_AUTHORSHIP_PROBLEM = (
    "В сообщении коммита соавторство или приписка «Generated with» — по правилам проекта их нет. "
    "Убери строку и повтори коммит."
)
BRANCH_TYPES = "feat|feature|fix|bugfix|hotfix|release|chore|docs|refactor|test|ci|build|perf|style|ai|claude|codex|copilot|cursor|opencode"
BRANCH_PART = r"[a-z0-9]+(?:[.-][a-z0-9]+)*"
BRANCH_NAME = re.compile(rf"^(?:main|master|develop|(?:{BRANCH_TYPES})/{BRANCH_PART}(?:/{BRANCH_PART})*)$")
# ./gradlew, ./mvnw at the start of a command or after ; & | ( — wrappers ship a .bat or .cmd twin for Windows
WRAPPER_PATTERN = re.compile(r"(^|[\s;&|(])\./([\w.-]+)(?=$|[\s;&|)])")
WINDOWS_WRAPPER_SUFFIXES = (".bat", ".cmd", ".exe")
TOOL_MISSING_MARKERS = (
    "command not found",
    "not recognized as an internal or external command",
    "не является внутренней или внешней",
    "canceled due to missing packages",
    "npm error 404",
    "could not determine executable to run",
    "no such file or directory",
    "failed to spawn",
)
FILE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
PATCH_TOOLS = {"apply_patch"}


# ---------------------------------------------------------------------------
# Input


def project_dir(event: dict) -> Path:
    """The project the kit is installed in: the nearest folder with .aikit/ above the session cwd."""
    start = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()).resolve()
    for folder in (start, *start.parents):
        if (folder / ".aikit").is_dir():
            return folder
    return start


def session_cwd(event: dict) -> Path:
    return Path(event.get("cwd") or os.getcwd()).resolve()


def patch_files(patch: str) -> list[tuple[str, str]]:
    """(path, added text) for every file an apply_patch body touches; deleted files are skipped."""
    files: list[tuple[str, list[str]]] = []
    for line in patch.splitlines():
        match = re.match(r"^\*\*\* (Add|Update|Delete) File: (.+)$", line)
        moved = re.match(r"^\*\*\* Move to: (.+)$", line)
        if match:
            files.append((match.group(2).strip(), []) if match.group(1) != "Delete" else ("", []))
        elif moved and files:
            files[-1] = (moved.group(1).strip(), files[-1][1])
        elif line.startswith("+") and files:
            files[-1][1].append(line[1:])
    return [(path, "\n".join(added)) for path, added in files if path]


def written_files(event: dict) -> list[tuple[Path, str]]:
    """Absolute path and written text of every file the tool call writes."""
    tool, data = event.get("tool_name", ""), event.get("tool_input") or {}
    cwd = session_cwd(event)
    if tool in FILE_TOOLS:
        path = data.get("file_path") or data.get("notebook_path") or ""
        texts = [data.get("content", ""), data.get("new_string", ""), data.get("new_source", "")]
        texts += [edit.get("new_string", "") for edit in data.get("edits", []) if isinstance(edit, dict)]
        return [(cwd / path, "\n".join(text for text in texts if isinstance(text, str)))] if path else []
    if tool in PATCH_TOOLS:
        patch = data.get("command") or data.get("patch") or data.get("input") or ""
        if isinstance(patch, list):
            patch = "\n".join(str(part) for part in patch)
        return [(cwd / path, text) for path, text in patch_files(str(patch))]
    return []


def shell_command(event: dict) -> str:
    if event.get("tool_name") in PATCH_TOOLS:
        return ""
    command = (event.get("tool_input") or {}).get("command", "")
    if isinstance(command, list):
        return shlex.join(str(part) for part in command)
    return command if isinstance(command, str) else ""


# ---------------------------------------------------------------------------
# PreToolUse: secrets, .env, commits, branches


QUOTES = "\"'"


def is_env_file(name: str) -> bool:
    base = Path(name.strip(QUOTES)).name
    if base == ".env":
        return True
    if not base.startswith(".env."):
        return False
    return base.split(".")[-1] not in ENV_TEMPLATE_SUFFIXES


def find_secret(text: str) -> str | None:
    for label, pattern in SECRET_PATTERNS.items():
        if re.search(pattern, text):
            return label
    return None


POWERSHELL_WRITE = re.compile(
    r"(?i)(?<![\w-])(?:set-content|add-content|out-file|new-item|tee-object|sc|ac)(?![\w-])([^;|&\n()]*)"
)
POWERSHELL_PATH_PARAMS = ("-path", "-literalpath", "-filepath", "-pspath", "-lp", "-name")
POWERSHELL_SWITCHES = {"-force", "-nonewline", "-append", "-noclobber", "-passthru", "-whatif", "-confirm"}
DOTNET_WRITE = re.compile(r"(?i)\[(?:system\.)?io\.file\]::(?:write|append)all(?:text|lines|bytes)\(\s*(['\"])([^'\"]+)\1")
POWERSHELL_TOKEN = re.compile(r"'[^']*'|\"[^\"]*\"|\S+")


def powershell_targets(command: str) -> list[str]:
    """Files that PowerShell write cmdlets and [IO.File]::Write* calls in the command write to."""
    targets = [match.group(2) for match in DOTNET_WRITE.finditer(command)]
    for match in POWERSHELL_WRITE.finditer(command):
        tokens = POWERSHELL_TOKEN.findall(match.group(1))
        positional_seen = False
        index = 0
        while index < len(tokens):
            token = tokens[index]
            name, _, attached = token.partition(":") if token.startswith("-") else ("", "", "")
            name = name.lower()
            if not name:
                if not positional_seen:
                    targets.append(token)
                    positional_seen = True
            elif any(param.startswith(name) for param in POWERSHELL_PATH_PARAMS) and len(name) > 2:
                positional_seen = True
                if attached:
                    targets.append(attached)
                elif index + 1 < len(tokens):
                    targets.append(tokens[index + 1])
                    index += 1
            elif name not in POWERSHELL_SWITCHES and not attached:
                index += 1
            index += 1
    return targets


HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)\n\s*\2(?=\s|$|\))", re.DOTALL)


def split_commands(command: str) -> tuple[list[list[str]], dict[str, str]]:
    """Simple commands of a shell line as token lists; heredoc bodies are replaced by placeholders."""
    bodies: dict[str, str] = {}

    def keep_body(match: re.Match) -> str:
        key = f"__AIKIT_HEREDOC_{len(bodies)}__"
        bodies[key] = match.group(3)
        return f" {key} "

    lexer = shlex.shlex(HEREDOC.sub(keep_body, command), posix=True, punctuation_chars=";&|()\n")
    lexer.whitespace_split = True
    lexer.commenters = ""
    commands, current = [], []
    for token in lexer:
        if token and set(token) <= set(";&|()\n"):
            if current:
                commands.append(current)
            current = []
        else:
            current.append(token)
    if current:
        commands.append(current)
    return commands, bodies


def git_subcommand(tokens: list[str]) -> tuple[str, list[str], str]:
    """("commit", args, dir) for `git [-C dir] [-c k=v] commit args`; ("", [], "") for anything else."""
    while tokens and re.match(r"^\w+=", tokens[0]):
        tokens = tokens[1:]
    if not tokens or Path(tokens[0]).name not in {"git", "git.exe"}:
        return "", [], ""
    index = 1
    directory = ""
    while index < len(tokens) and tokens[index].startswith("-"):
        if tokens[index] == "-C" and index + 1 < len(tokens):
            directory = tokens[index + 1]
        index += 2 if tokens[index] in {"-C", "-c"} else 1
    if index >= len(tokens):
        return "", [], ""
    return tokens[index], tokens[index + 1 :], directory


def resolve_heredocs(text: str, bodies: dict[str, str]) -> str:
    for key, body in bodies.items():
        text = text.replace(key, body)
    return re.sub(r"^\$\(\s*cat\s*(.*?)\s*\)$", r"\1", text.strip(), flags=re.DOTALL).strip()


def commit_message(args: list[str], bodies: dict[str, str], cwd: Path) -> str | None:
    """The message a `git commit` call sets, or None when git opens an editor or reuses a message."""
    parts: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in {"-m", "--message"} and index + 1 < len(args):
            parts.append(resolve_heredocs(args[index + 1], bodies))
            index += 1
        elif arg.startswith("--message="):
            parts.append(resolve_heredocs(arg.split("=", 1)[1], bodies))
        elif arg.startswith("-m") and len(arg) > 2 and not arg.startswith("--"):
            parts.append(resolve_heredocs(arg[2:], bodies))
        elif arg in {"-F", "--file"} and index + 1 < len(args):
            message_file = cwd / args[index + 1]
            if message_file.is_file():
                parts.append(message_file.read_text(encoding="utf-8", errors="replace"))
            index += 1
        index += 1
    return "\n\n".join(parts) if parts else None


def check_commit(message: str) -> str | None:
    subject = message.strip().splitlines()[0] if message.strip() else ""
    if CO_AUTHORSHIP.search(message):
        return CO_AUTHORSHIP_PROBLEM
    if COMMIT_EXEMPT.match(subject) or COMMIT_SUBJECT.match(subject):
        return None
    return (
        f"Сообщение коммита «{subject}» не по Conventional Commits. "
        "Формат: <type>[(scope)][!]: <описание>, type — один из "
        f"{COMMIT_TYPES.replace('|', ', ')}. Пример: «feat(auth): добавлена авторизация через OAuth»."
    )


def created_branch(subcommand: str, args: list[str]) -> str | None:
    """Name of the branch a git call creates or renames to, if any."""
    def value_after(flags: set[str]) -> str | None:
        for index, arg in enumerate(args):
            if arg in flags and index + 1 < len(args):
                return args[index + 1]
        return None

    if subcommand == "checkout":
        return value_after({"-b", "-B"})
    if subcommand == "switch":
        return value_after({"-c", "-C", "--create", "--force-create"})
    if subcommand == "worktree" and args[:1] == ["add"]:
        return value_after({"-b", "-B"})
    if subcommand == "branch":
        flags = {arg for arg in args if arg.startswith("-")}
        positionals = [arg for arg in args if not arg.startswith("-")]
        if not positionals or flags - {"-f", "--force", "-t", "--track", "--no-track", "-m", "-M", "-c", "-C", "--move", "--copy"}:
            return None
        if flags & {"-m", "-M", "-c", "-C", "--move", "--copy"}:
            return positionals[-1]
        return positionals[0]
    return None


def check_branch(name: str) -> str | None:
    if BRANCH_NAME.match(name):
        return None
    return (
        f"Имя ветки «{name}» не по Conventional Branch. Формат: <type>/<описание>, "
        "type — feat, fix, hotfix, release, chore (или docs, refactor, test, ci, build, perf, style), "
        "описание — строчная латиница, цифры и дефисы. Пример: feat/oauth-login."
    )


def env_files_to_stage(args: list[str], cwd: Path) -> list[str]:
    """.env files a `git add` call would stage: named explicitly or picked up by a directory or -A."""
    paths = [arg for arg in args if not arg.startswith("-")]
    named = [path for path in paths if is_env_file(path)]
    if named:
        return named
    staging_all = not paths and bool({"-A", "--all"} & set(args))
    if not paths and not staging_all:
        return []
    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--modified", "--exclude-standard", "--", *(paths or ["."])],
            cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=FORMAT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return [line for line in result.stdout.splitlines() if is_env_file(line)]


def check_shell(event: dict) -> str | None:
    command = shell_command(event)
    if not command:
        return None
    targets = re.findall(r"(?:>>?|\btee(?:\s+-a)?)\s*([^\s;&|<>]+)", command) + powershell_targets(command)
    for target in targets:
        if is_env_file(target.replace("\\", "/")):
            return f"Запись в {target.strip(QUOTES)} заблокирована: .env-файлы с секретами правит только человек."
    secret = find_secret(command)
    if secret and (re.search(r">|\btee\b|\becho\b|\bprintf\b|\bgit\s+commit\b", command) or POWERSHELL_WRITE.search(command) or DOTNET_WRITE.search(command)):
        return f"В команде {secret} — секреты не пишутся в файлы и коммиты. Используй переменную окружения."
    try:
        commands, bodies = split_commands(command)
    except ValueError:
        # Unbalanced quotes: only the co-authorship rule can still be checked reliably
        if re.search(r"\bgit\b.*\bcommit\b", command) and CO_AUTHORSHIP.search(command):
            return CO_AUTHORSHIP_PROBLEM
        return None
    cwd = session_cwd(event)
    for tokens in commands:
        subcommand, args, directory = git_subcommand(tokens)
        git_cwd = cwd / directory
        if subcommand == "add":
            staged = env_files_to_stage(args, git_cwd)
            if staged:
                return (
                    f"git add добавит в индекс {', '.join(staged)} — .env-файлы с секретами не коммитятся. "
                    "Добавь их в .gitignore и укажи нужные файлы явно."
                )
        elif subcommand == "commit":
            message = commit_message(args, bodies, git_cwd)
            problem = check_commit(message) if message is not None else None
            if problem:
                return problem
        branch = created_branch(subcommand, args) if subcommand else None
        if branch:
            problem = check_branch(branch)
            if problem:
                return problem
    return None


def check_files(event: dict) -> str | None:
    for path, text in written_files(event):
        if is_env_file(path.name):
            return f"Запись в {path.name} заблокирована: .env-файлы с секретами правит только человек. Пример значений — в .env.example."
        secret = find_secret(text)
        if secret:
            return (
                f"В тексте для {path.name} {secret}. Секреты не хранятся в коде и конфигах — "
                "читай их из переменной окружения."
            )
    return None


def pre_tool_use(event: dict) -> int:
    problem = check_files(event) or check_shell(event)
    if not problem:
        return 0
    if DENY_JSON_FLAG in sys.argv[1:]:
        emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": f"AIKit: {problem}"}})
        return 0
    print(f"AIKit: {problem}", file=sys.stderr)
    return BLOCK_EXIT_CODE


# ---------------------------------------------------------------------------
# Profiles and commands


def load_profiles(project: Path) -> dict[str, dict]:
    try:
        data = json.loads((project / PROFILES_FILE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    profiles = data.get("profiles", {}) if isinstance(data, dict) else {}
    return {name: spec for name, spec in profiles.items() if isinstance(spec, dict)}


def checkout_for(path: Path, project: Path) -> Path:
    """The checkout that holds the file: a worktree of /implement-feature --worktree or the project itself."""
    worktrees = (project / WORKTREES_DIR).resolve()
    try:
        parts = path.relative_to(worktrees).parts
    except ValueError:
        return project
    return worktrees / parts[0] if len(parts) > 1 else project


def profile_for(path: Path, checkout: Path, profiles: dict[str, dict]) -> tuple[str, Path] | None:
    """The profile whose root holds the file (the deepest root wins) and that treats it as code."""
    best: tuple[int, str, Path] | None = None
    for name, spec in profiles.items():
        root = (checkout / str(spec.get("root") or ".")).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        extensions = spec.get("code_extensions") or []
        if extensions and path.suffix.lower() not in extensions:
            continue
        depth = len(root.parts)
        if best is None or depth > best[0]:
            best = (depth, name, root)
    return (best[1], best[2]) if best else None


def decode_output(data: bytes) -> str:
    """Tools print UTF-8; cmd.exe itself prints its errors in the OEM code page."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("oem" if os.name == "nt" else "latin-1", errors="replace")


def windows_wrappers(command: str, root: Path) -> str:
    """cmd.exe does not run ./gradlew or ./mvnw: point it at the gradlew.bat / mvnw.cmd next to the script."""
    def replace(match: re.Match) -> str:
        name = match.group(2)
        if any((root / f"{name}{suffix}").is_file() for suffix in WINDOWS_WRAPPER_SUFFIXES):
            return f"{match.group(1)}.\\{name}"
        return match.group(0)
    return WRAPPER_PATTERN.sub(replace, command)


def run_command(template: str, root: Path, files: list[str], timeout: int) -> tuple[int, str] | None:
    """Exit code and output of a profile command; None when its tool is not installed or it timed out."""
    quote = (lambda item: f'"{item}"') if os.name == "nt" else shlex.quote
    command = template.replace("{files}", " ".join(quote(item) for item in files))
    if os.name == "nt":
        command = windows_wrappers(command, root)
    # npx must not download a tool the project does not have: that is slow and the tool has no config here
    env = {**os.environ, "npm_config_yes": "false"}
    try:
        result = subprocess.run(
            command, shell=True, cwd=root, env=env, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = (decode_output(result.stdout) + decode_output(result.stderr)).strip()
    if result.returncode != 0 and any(marker in output.lower() for marker in TOOL_MISSING_MARKERS):
        return None
    if result.returncode in {127, 9009}:
        return None
    return result.returncode, output


def tail(text: str) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-OUTPUT_TAIL_LINES:])


# ---------------------------------------------------------------------------
# Session state: changed files between Stop events


def state_path(project: Path, session_id: str) -> Path:
    key = hashlib.sha1(f"{project}|{session_id}".encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / "aikit-hooks" / f"{key}.json"


def read_state(project: Path, session_id: str) -> dict:
    try:
        return json.loads(state_path(project, session_id).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def pending_profiles(state: dict, project: Path) -> list[tuple[str, str]]:
    """Profiles with changed code and the checkout they were changed in."""
    items = []
    for item in state.get("pending", []):
        if isinstance(item, str):
            items.append((item, str(project)))
        elif isinstance(item, list) and len(item) == 2:
            items.append((str(item[0]), str(item[1])))
    return items


def write_state(project: Path, session_id: str, state: dict) -> None:
    path = state_path(project, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# PostToolUse: format and lint the changed file


def post_tool_use(event: dict) -> int:
    project = project_dir(event)
    profiles = load_profiles(project)
    if not profiles:
        return 0
    session_id = str(event.get("session_id") or "default")
    state = read_state(project, session_id)
    pending = {tuple(item) for item in pending_profiles(state, project)}
    touched = set(state.get("touched", []))
    reports = []
    for path, _ in written_files(event):
        if not path.is_file():
            continue
        checkout = checkout_for(path.resolve(), project)
        match = profile_for(path.resolve(), checkout, profiles)
        if not match:
            continue
        name, root = match
        relative = path.resolve().relative_to(root).as_posix()
        pending.add((name, str(checkout)))
        touched.add(path.resolve().as_posix())
        commands = profiles[name].get("commands", {})
        if commands.get("format") and "{files}" in commands["format"]:
            run_command(commands["format"], root, [relative], FORMAT_TIMEOUT_SECONDS)
        if commands.get("lint") and "{files}" in commands["lint"]:
            result = run_command(commands["lint"], root, [relative], LINT_TIMEOUT_SECONDS)
            if result and result[0] != 0:
                reports.append(f"Линтер профиля {name} нашёл проблемы в {relative}:\n{tail(result[1])}")
    write_state(project, session_id, {**state, "pending": sorted([list(item) for item in pending]), "touched": sorted(touched)})
    if reports:
        emit({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "AIKit: " + "\n\n".join(reports)}})
    return 0


# ---------------------------------------------------------------------------
# Stop: tests after code changes, /capture-memory after a large task


def stop(event: dict) -> int:
    project = project_dir(event)
    profiles = load_profiles(project)
    session_id = str(event.get("session_id") or "default")
    state = read_state(project, session_id)
    output: dict = {}
    notes = []
    failures = []
    for name, checkout in pending_profiles(state, project):
        test = profiles.get(name, {}).get("commands", {}).get("test")
        if not test or not Path(checkout).is_dir():
            continue
        root = (Path(checkout) / str(profiles[name].get("root") or ".")).resolve()
        where = root.relative_to(project).as_posix() if root.is_relative_to(project) else str(root)
        result = run_command(test, root, [], TEST_TIMEOUT_SECONDS)
        if result is None:
            notes.append(f"код профиля {name} изменён, но тесты не запустились (`{test}` в {where}) — проверь вручную")
        elif result[0] != 0:
            failures.append(f"Тесты профиля {name} упали (`{test}` в {where}):\n{tail(result[1])}")
    if failures and not event.get("stop_hook_active"):
        output.update({"decision": "block", "reason": "AIKit: " + "\n\n".join(failures) + "\n\nИсправь код или тесты и запусти их снова."})
    elif failures:
        notes.append("тесты всё ещё падают — см. вывод выше")
    touched = state.get("touched", [])
    keeps_memory = (project / MEMORY_DIR).is_dir()
    if keeps_memory and len(touched) >= LARGE_TASK_FILES and not state.get("memory_suggested"):
        notes.append(f"изменено {len(touched)} файлов — зафиксируй решения и коррекции через /capture-memory")
        state["memory_suggested"] = True
    if notes:
        output["systemMessage"] = "AIKit: " + "; ".join(notes)
    write_state(project, session_id, {**state, "pending": []})
    emit(output)
    return 0


# ---------------------------------------------------------------------------
# SessionStart: project memory and product context


def read_context_file(path: Path, label: str) -> str | None:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text:
        return None
    if len(text) > CONTEXT_FILE_LIMIT:
        text = text[:CONTEXT_FILE_LIMIT] + f"\n… (обрезано, полный текст — {label})"
    return f"## {label}\n\n{text}"


def has_memory_entries(text: str) -> bool:
    return any(line.lstrip().startswith(("-", "|", "*")) for line in text.splitlines())


def version_key(value: object) -> tuple[int, int, int] | None:
    match = SEMVER.match(value.strip()) if isinstance(value, str) else None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3))) if match else None


def local_version() -> str:
    """Version of the installed plugin: VERSION at its root, else "version" of its Claude Code manifest."""
    try:
        return (PLUGIN_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        pass
    try:
        manifest = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    version = manifest.get("version") if isinstance(manifest, dict) else None
    return version if isinstance(version, str) else ""


def update_cache_path() -> Path:
    if os.environ.get(UPDATE_CACHE_ENV):
        return Path(os.environ[UPDATE_CACHE_ENV])
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        base = Path(os.environ["LOCALAPPDATA"])
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "aikit" / "update-check.json"


def read_update_cache() -> dict:
    try:
        data = json.loads(update_cache_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_update_cache(data: dict) -> None:
    path = update_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    os.replace(temporary, path)


def now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def cache_is_fresh(cache: dict) -> bool:
    try:
        checked = datetime.datetime.fromisoformat(str(cache.get("checked_at")))
    except ValueError:
        return False
    return checked.tzinfo is not None and now_utc() - checked < UPDATE_CHECK_INTERVAL


def refresh_update_cache() -> int:
    """Detached run: fetch VERSION from main into the cache. Offline or any error — keep the old value quietly."""
    cache = read_update_cache()
    try:
        url = os.environ.get(UPDATE_URL_ENV) or UPDATE_URL
        with urllib.request.urlopen(url, timeout=UPDATE_TIMEOUT_SECONDS) as response:
            remote = response.read(UPDATE_RESPONSE_LIMIT).decode("utf-8", errors="replace").strip()
        if version_key(remote):
            cache["remote_version"] = remote
    except Exception:  # noqa: BLE001 — offline, proxy, timeout: no notice and no noise
        pass
    cache["checked_at"] = now_utc().isoformat(timespec="seconds")
    try:
        write_update_cache(cache)
    except OSError:
        pass
    return 0


def start_update_refresh() -> None:
    """Fetch in a detached process: the session start never waits for the network."""
    options: dict = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "close_fds": True}
    if os.name == "nt":
        options["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        options["start_new_session"] = True
    try:
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), REFRESH_UPDATE_FLAG], **options)
    except OSError:
        pass


def update_check_enabled(project: Path) -> bool:
    if os.environ.get(NO_UPDATE_CHECK_ENV, "").strip().lower() in {"1", "true", "yes"}:
        return False
    try:
        settings = json.loads((project / SETTINGS_FILE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    return not (isinstance(settings, dict) and settings.get("update_check") is False)


def update_notice(project: Path) -> str | None:
    """Once per version per machine: main has a newer AIKit than the installed plugin."""
    if not update_check_enabled(project):
        return None
    local = local_version()
    local_key = version_key(local)
    if not local_key:
        return None
    cache = read_update_cache()
    if not cache_is_fresh(cache):
        start_update_refresh()
    remote = cache.get("remote_version")
    remote_key = version_key(remote)
    if not remote_key or remote_key <= local_key or cache.get("notified_version") == remote:
        return None
    try:
        write_update_cache({**cache, "notified_version": remote})
    except OSError:
        return None
    return (
        f"AIKit: доступна версия {remote} (у вас {local}). "
        "Claude: /plugin marketplace update aikit, затем /plugin update aikit@aikit (так же — плагины профилей и паков) "
        "и перезапуск сессии; Codex: codex plugin marketplace upgrade"
    )


def runs_in_codex() -> bool:
    """Codex gives plugin hooks PLUGIN_ROOT, Claude Code gives CLAUDE_PLUGIN_ROOT."""
    return bool(os.environ.get("PLUGIN_ROOT")) and not os.environ.get("CLAUDE_PLUGIN_ROOT")


def session_start(event: dict) -> int:
    project = project_dir(event)
    output: dict = {}
    notice = update_notice(project) if PLUGIN_FLAG in sys.argv[1:] else None
    if notice:
        output["systemMessage"] = notice
    parts = []
    index = read_context_file(project / MEMORY_INDEX, MEMORY_INDEX.as_posix())
    if index and has_memory_entries(index):
        parts.append(index)
    product = read_context_file(project / PRODUCT_FILE, PRODUCT_FILE.as_posix())
    if product and PRODUCT_TEMPLATE_MARKER not in product:
        parts.append(product)
    if notice and runs_in_codex():
        # Codex may not show systemMessage of SessionStart: the agent passes the notice on
        parts.append(f"Передай пользователю в первом ответе одной строкой: {notice}")
    if parts:
        context = "Контекст проекта от AIKit (память команды и описание продукта):\n\n" + "\n\n".join(parts)
        output["hookSpecificOutput"] = {"hookEventName": "SessionStart", "additionalContext": context}
    emit(output)
    return 0


# ---------------------------------------------------------------------------


def emit(data: dict) -> None:
    sys.stdout.write(json.dumps(data, ensure_ascii=False) if data else "{}")


HANDLERS = {
    "PreToolUse": pre_tool_use,
    "PostToolUse": post_tool_use,
    "Stop": stop,
    "SessionStart": session_start,
}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if REFRESH_UPDATE_FLAG in sys.argv[1:]:
        return refresh_update_cache()
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        event = json.loads(raw) if raw.strip() else {}
        if PLUGIN_FLAG in sys.argv[1:] and not (project_dir(event) / ".aikit").is_dir():
            return 0
        handler = HANDLERS.get(str(event.get("hook_event_name", "")))
        return handler(event) if handler else 0
    except Exception as error:  # noqa: BLE001 — a broken hook must not block the agent
        print(f"AIKit hook: внутренняя ошибка, действие не проверено: {error}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
