#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Antigravity lifecycle entry point; policy logic is shared with the other runtimes."""

import io
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True
EVENT_FLAG = "--event"
MIN_PYTHON = (3, 9)


def parse_event_arg(argv):
    for index, arg in enumerate(argv):
        if arg == EVENT_FLAG and index + 1 < len(argv):
            return argv[index + 1]
        if arg.startswith(EVENT_FLAG + "="):
            return arg.split("=", 1)[1]
    return ""


def default_allow_payload(event_name):
    if event_name in ("PreToolUse", "Stop"):
        return {"decision": "allow"}
    return {}


def emit_json(data):
    text = json.dumps(data, ensure_ascii=False) if data else "{}"
    if sys.version_info[0] < 3 and isinstance(text, unicode):  # noqa: F821
        text = text.encode("utf-8")
    sys.stdout.write(text)
    sys.stdout.flush()


def delegate_to_python3():
    """When `python` on PATH is Python 2 or < 3.9, forward stdin to python3 / py -3; fail-open on error."""
    raw_stdin = getattr(sys.stdin, "buffer", sys.stdin).read()
    script = os.path.abspath(__file__)
    args = sys.argv[1:]
    check = "import sys;sys.exit(0 if sys.version_info[:2]>=(3,9) else 1)"
    for candidate in (["python3"], ["py", "-3"]):
        try:
            if subprocess.call(candidate + ["-c", check], stdout=subprocess.PIPE, stderr=subprocess.PIPE) != 0:
                continue
            proc = subprocess.Popen(
                candidate + [script] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            out, err = proc.communicate(raw_stdin)
            if out:
                getattr(sys.stdout, "buffer", sys.stdout).write(out)
                sys.stdout.flush()
            else:
                emit_json(default_allow_payload(parse_event_arg(args)))
            if err:
                getattr(sys.stderr, "buffer", sys.stderr).write(err)
                sys.stderr.flush()
            return proc.returncode if proc.returncode == 0 else 0
        except OSError:
            continue
    emit_json(default_allow_payload(parse_event_arg(args)))
    return 0


if sys.version_info[:2] < MIN_PYTHON:
    raise SystemExit(delegate_to_python3())

import importlib.util  # noqa: E402
from pathlib import Path  # noqa: E402
from urllib.parse import unquote, urlparse  # noqa: E402

installed = Path(__file__).resolve().parents[1] / "aikit_hook.py"
source = Path(__file__).resolve().parents[2] / "hooks/aikit_hook.py"
engine = installed if installed.is_file() else source
spec = importlib.util.spec_from_file_location("aikit_hook_engine", engine)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def normalize_workspace_path(raw_path):
    text = raw_path.strip()
    if text.startswith("file://"):
        parsed = urlparse(text)
        path_text = unquote(parsed.path or "")
        if os.name == "nt" and path_text.startswith("/") and len(path_text) >= 3 and path_text[2] == ":":
            path_text = path_text[1:]
        return Path(path_text).resolve()
    return Path(text).resolve()


def resolve_cwd(raw_event):
    workspace_paths = raw_event.get("workspacePaths")
    if isinstance(workspace_paths, list) and workspace_paths:
        candidates = [normalize_workspace_path(str(item)) for item in workspace_paths if str(item).strip()]
        for candidate in candidates:
            for folder in [candidate] + list(candidate.parents):
                if (folder / ".aikit").is_dir():
                    return candidate
        if candidates:
            return candidates[0]
    if raw_event.get("cwd"):
        return Path(str(raw_event["cwd"])).resolve()
    return Path(os.getcwd()).resolve()


def infer_event_name(raw_event, argv):
    explicit = parse_event_arg(argv) or str(raw_event.get("hook_event_name") or raw_event.get("hookEventName") or "")
    if explicit:
        return explicit
    if "terminationReason" in raw_event or "executionNum" in raw_event:
        return "Stop"
    if "toolCall" in raw_event:
        return "PostToolUse" if "error" in raw_event else "PreToolUse"
    if "invocationNum" in raw_event:
        return "PostInvocation"
    return "SessionStart"


def translate_tool_call(raw_event):
    if raw_event.get("tool_name"):
        return str(raw_event["tool_name"]), dict(raw_event.get("tool_input") or {})
    tool_call = raw_event.get("toolCall")
    if not isinstance(tool_call, dict):
        return "", {}
    name = str(tool_call.get("name") or tool_call.get("toolName") or "")
    raw_args = tool_call.get("args") if isinstance(tool_call.get("args"), dict) else tool_call.get("arguments")
    args = raw_args if isinstance(raw_args, dict) else {}
    if name in {"run_command", "bash", "Bash"}:
        command = args.get("CommandLine") if "CommandLine" in args else args.get("command", "")
        return "Bash", {"command": command}
    if name in {"write_file", "write_to_file", "Write"}:
        path = args.get("Path") or args.get("TargetFile") or args.get("file_path") or ""
        content = args.get("Content") if "Content" in args else (args.get("CodeContent") or args.get("content") or "")
        return "Write", {"file_path": path, "content": content}
    if name in {"edit_file", "replace_file_content", "multi_replace_file_content", "Edit", "MultiEdit"}:
        path = args.get("Path") or args.get("TargetFile") or args.get("file_path") or ""
        new_string = (
            args.get("Replacement")
            if "Replacement" in args
            else (args.get("ReplacementContent") or args.get("new_string") or "")
        )
        chunks = args.get("ReplacementChunks") if isinstance(args.get("ReplacementChunks"), list) else []
        edits = [
            {"new_string": str(chunk.get("ReplacementContent") or chunk.get("new_string") or "")}
            for chunk in chunks
            if isinstance(chunk, dict)
        ]
        return "Edit", {"file_path": path, "new_string": new_string, "edits": edits}
    if name == "apply_patch":
        return "apply_patch", dict(args)
    return name, dict(args)


def capture_engine_call(fn, event):
    buffer = io.StringIO()
    original_stdout = sys.stdout
    try:
        sys.stdout = buffer
        fn(event)
    finally:
        sys.stdout = original_stdout
    text = buffer.getvalue().strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def handle_event(event_name, raw_event, engine_event, project):
    session_id = str(engine_event.get("session_id") or "default")
    if event_name == "PreToolUse":
        problem = module.check_files(engine_event) or module.check_shell(engine_event)
        if problem:
            return {"decision": "deny", "reason": "AIKit: {}".format(problem)}
        return {"decision": "allow"}

    if event_name == "PostToolUse":
        result = capture_engine_call(module.post_tool_use, engine_event)
        context = result.get("hookSpecificOutput", {}).get("additionalContext")
        if context:
            state = module.read_state(project, session_id)
            reports = list(state.get("lint_reports", []))
            reports.append(str(context))
            module.write_state(project, session_id, dict(state, lint_reports=reports))
        return {}

    if event_name == "PostInvocation":
        state = module.read_state(project, session_id)
        reports = [str(item) for item in state.get("lint_reports", []) if str(item).strip()]
        if not reports:
            return {}
        next_state = {key: value for key, value in state.items() if key != "lint_reports"}
        module.write_state(project, session_id, next_state)
        return {"injectSteps": [{"ephemeralMessage": "\n\n".join(reports)}]}

    if event_name == "Stop":
        reason_code = str(raw_event.get("terminationReason") or "NO_TOOL_CALL")
        if reason_code not in {"", "NO_TOOL_CALL", "COMPLETE"}:
            return {"decision": "allow"}
        state = module.read_state(project, session_id)
        stop_active = bool(raw_event.get("stop_hook_active") or state.get("stop_continued"))
        stop_event = dict(engine_event, stop_hook_active=stop_active)
        result = capture_engine_call(module.stop, stop_event)
        updated_state = module.read_state(project, session_id)
        if result.get("decision") == "block" and result.get("reason"):
            module.write_state(project, session_id, dict(updated_state, stop_continued=True))
            return {"decision": "continue", "reason": str(result["reason"])}
        if "stop_continued" in updated_state:
            updated_state.pop("stop_continued", None)
            module.write_state(project, session_id, updated_state)
        return {"decision": "allow"}

    if event_name == "SessionStart":
        result = capture_engine_call(module.session_start, engine_event)
        messages = []
        if result.get("systemMessage"):
            messages.append(str(result["systemMessage"]))
        context = result.get("hookSpecificOutput", {}).get("additionalContext")
        if context:
            messages.append(str(context))
        if not messages:
            return {}
        return {"injectSteps": [{"systemMessage": {"systemMessage": "\n\n".join(messages)}}]}

    return {}


def main():
    os.environ["AIKIT_HOOK_RUNTIME"] = "antigravity"
    os.environ.pop("CLAUDE_PROJECT_DIR", None)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if module.REFRESH_UPDATE_FLAG in sys.argv[1:]:
        return module.refresh_update_cache()
    if module.STATUS_FLAG in sys.argv[1:]:
        module.emit(module.hook_status(module.project_dir({})))
        return 0

    event_name, project = "", None
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        raw_event = json.loads(raw) if raw.strip() else {}
        event_name = infer_event_name(raw_event, sys.argv[1:])
        cwd = resolve_cwd(raw_event)
        session_id = str(raw_event.get("conversationId") or raw_event.get("session_id") or "default")
        tool_name, tool_input = translate_tool_call(raw_event)
        engine_event = {
            "hook_event_name": event_name,
            "session_id": session_id,
            "cwd": str(cwd),
            "tool_name": tool_name,
            "tool_input": tool_input,
        }
        project = module.project_dir(engine_event)
        if module.PLUGIN_FLAG in sys.argv[1:] and not (project / ".aikit").is_dir():
            module.emit(default_allow_payload(event_name))
            return 0
        payload = handle_event(event_name, raw_event, engine_event, project)
        module.emit(payload)
        module.record_run(project, event_name)
        return 0
    except Exception as error:  # noqa: BLE001 — never block the agent on an internal hook error
        sys.stderr.write("AIKit hook: внутренняя ошибка, действие не проверено: {}\n".format(error))
        if project is not None:
            module.record_run(project, event_name or "unknown", "{}: {}".format(type(error).__name__, error))
        module.emit(default_allow_payload(event_name))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
