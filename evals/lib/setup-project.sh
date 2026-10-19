#!/usr/bin/env bash
# Prepare the eval workspace (the current directory): copy a fixture project and connect it to AIKit.
#
#   setup-project.sh <profiles> [fixture]
#
# AIKIT_EVAL_RUNTIME=claude (default): .aikit/ via scripts/plugin-init.py — the plugins under test bring agents, skills and hooks.
# AIKIT_EVAL_RUNTIME=codex: the Codex adapter installer — skills, agents and hooks land in the project itself.
#
# Profile commands are removed from .aikit/profiles.json: the fixtures have no node_modules or virtualenv,
# and hook results must not depend on the tools installed on the machine that runs the evals.
set -euo pipefail

profiles="$1"
fixture="${2:-}"
lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]//\\//}")" && pwd)"
evals_dir="$(dirname "$lib_dir")"
kit_dir="$(dirname "$evals_dir")"

python_bin=python3
if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
  python_bin=python
fi

if [[ -n "$fixture" ]]; then
  cp -R "$evals_dir/fixtures/$fixture/." .
fi

case "${AIKIT_EVAL_RUNTIME:-claude}" in
  claude) "$python_bin" "$kit_dir/scripts/plugin-init.py" --runtime claude --profiles "$profiles" --workspace . >/dev/null ;;
  codex) "$python_bin" "$kit_dir/scripts/install-adapter-package.py" codex --profile "$profiles" --workspace . >/dev/null ;;
  *) echo "unknown AIKIT_EVAL_RUNTIME: $AIKIT_EVAL_RUNTIME" >&2; exit 1 ;;
esac

"$python_bin" - <<'EOF'
import json
from pathlib import Path

path = Path(".aikit/profiles.json")
data = json.loads(path.read_text(encoding="utf-8"))
for spec in data.get("profiles", {}).values():
    spec["commands"] = {}
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
EOF
