#!/usr/bin/env python3
"""Codex lifecycle entry point; policy logic is shared with the other runtimes."""

import importlib.util
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
installed = Path(__file__).resolve().parents[1] / "aikit_hook.py"
source = Path(__file__).resolve().parents[2] / "hooks/aikit_hook.py"
engine = installed if installed.is_file() else source
spec = importlib.util.spec_from_file_location("aikit_hook_engine", engine)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main() -> int:
    os.environ["AIKIT_HOOK_RUNTIME"] = "codex"
    os.environ.pop("CLAUDE_PROJECT_DIR", None)
    if module.DENY_JSON_FLAG not in sys.argv:
        sys.argv.append(module.DENY_JSON_FLAG)
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
