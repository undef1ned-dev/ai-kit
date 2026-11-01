#!/usr/bin/env bash
# update-agents.sh — Update AIKit plugins and rebuild project agents for Codex and Antigravity.
#
# Installed into <workspace>/.aikit/scripts/update-agents.sh during setup.
# Works on Linux, macOS and Windows (Git Bash).
#
# Usage:
#   bash .aikit/scripts/update-agents.sh                  # auto-detect connected runtimes, update plugins + rebuild agents
#   bash .aikit/scripts/update-agents.sh --agents-only    # only rebuild project agents from currently installed plugins
#   bash .aikit/scripts/update-agents.sh codex            # update only Codex
#   bash .aikit/scripts/update-agents.sh antigravity      # update only Antigravity
#   bash .aikit/scripts/update-agents.sh --workspace DIR  # explicit project workspace

set -eo pipefail
export PYTHONIOENCODING=utf-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WORKSPACE="."
if [[ "$(basename "$SCRIPT_DIR")" == "scripts" && "$(basename "$(dirname "$SCRIPT_DIR")")" == ".aikit" ]]; then
  DEFAULT_WORKSPACE="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

WORKSPACE="$DEFAULT_WORKSPACE"
AGENTS_ONLY=0
REQUESTED_RUNTIMES=()

usage() {
  cat <<'EOF'
Использование:
  bash .aikit/scripts/update-agents.sh [codex|antigravity ...] [--agents-only] [--workspace <путь>]

Без аргументов скрипт сам определяет подключённые в проекте runtime (codex, antigravity)
по .aikit/plugin-init.json (или папкам .codex/agents и .agents/agents), обновляет плагины AIKit
и пересобирает агентов проекта.

Флаги:
  codex             Обновить только для Codex
  antigravity       Обновить только для Antigravity
  --agents-only     Только пересобрать агентов проекта из уже установленных плагинов
  --with-plugins    Обновить плагины и пересобрать агентов (поведение по умолчанию)
  --workspace DIR   Путь к корню проекта (по умолчанию определяется автоматически)
  -h, --help        Показать эту справку
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    codex|antigravity)
      REQUESTED_RUNTIMES+=("$1")
      shift
      ;;
    --agents-only|--refresh-only)
      AGENTS_ONLY=1
      shift
      ;;
    --with-plugins)
      AGENTS_ONLY=0
      shift
      ;;
    --workspace)
      [[ $# -ge 2 ]] || { echo "AIKit: укажи путь после --workspace" >&2; exit 2; }
      WORKSPACE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "AIKit: неизвестный аргумент: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

WORKSPACE="$(cd "$WORKSPACE" && pwd)"

find_python() {
  local candidate
  for candidate in "${AIKIT_PYTHON:-}" python3 python; do
    [[ -n "$candidate" ]] || continue
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) and "WindowsApps" not in sys.executable else 1)' >/dev/null 2>&1; then
        echo "$candidate"
        return 0
      fi
    fi
  done
  if command -v py >/dev/null 2>&1; then
    if py -3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) and "WindowsApps" not in sys.executable else 1)' >/dev/null 2>&1; then
      echo "py -3"
      return 0
    fi
  fi
  return 1
}

PYTHON_CMD="$(find_python || true)"
if [[ -z "$PYTHON_CMD" ]]; then
  echo "AIKit: нужен Python 3.11+ в PATH (python3, python или py -3)." >&2
  exit 1
fi

run_py() {
  if [[ "$PYTHON_CMD" == "py -3" ]]; then
    py -3 "$@"
  else
    "$PYTHON_CMD" "$@"
  fi
}

detect_runtimes() {
  run_py - "$WORKSPACE" <<'PY'
import json
import sys
from pathlib import Path

workspace = Path(sys.argv[1])
state_file = workspace / ".aikit" / "plugin-init.json"
found = []

if state_file.is_file():
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    runtimes = state.get("runtimes")
    if not isinstance(runtimes, list):
        runtimes = [state.get("runtime")]
    for name in ("codex", "antigravity"):
        if name in runtimes:
            found.append(name)

if not found:
    if (workspace / ".codex" / "agents").is_dir():
        found.append("codex")
    if (workspace / ".agents" / "agents").is_dir():
        found.append("antigravity")

print(" ".join(found))
PY
}

if [[ ${#REQUESTED_RUNTIMES[@]} -eq 0 ]]; then
  DETECTED="$(detect_runtimes | tr -d '\r')"
  if [[ -z "$DETECTED" ]]; then
    echo "AIKit: в проекте ($WORKSPACE) не найдена установка для Codex или Antigravity." >&2
    echo "Сначала подключи проект через setup (Codex: \$aikit:setup, Antigravity: /setup)." >&2
    exit 1
  fi
  read -r -a TARGET_RUNTIMES <<< "$DETECTED"
else
  TARGET_RUNTIMES=("${REQUESTED_RUNTIMES[@]}")
fi

find_codex_kit_root() {
  if [[ -n "${AIKIT_ROOT:-}" && -f "${AIKIT_ROOT}/scripts/plugin-init.py" ]]; then
    (cd "$AIKIT_ROOT" && pwd)
    return 0
  fi
  if [[ -f "$SCRIPT_DIR/plugin-init.py" ]]; then
    echo "$(cd "$SCRIPT_DIR/.." && pwd)"
    return 0
  fi
  if command -v codex >/dev/null 2>&1; then
    local root
    root="$(run_py - "$WORKSPACE" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

workspace = Path(sys.argv[1])
try:
    res = subprocess.run(
        ["codex", "plugin", "list", "--marketplace", "aikit", "--json"],
        cwd=workspace,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if res.returncode == 0:
        data = json.loads(res.stdout)
        for rec in data.get("installed", []):
            if isinstance(rec, dict) and rec.get("name") == "aikit" and rec.get("marketplaceName") == "aikit":
                path = rec.get("source", {}).get("path", "")
                if path and (Path(path) / "scripts" / "plugin-init.py").is_file():
                    print(path)
                    break
except Exception:
    pass
PY
)"
    root="$(printf '%s' "$root" | tr -d '\r')"
    if [[ -n "$root" ]]; then
      echo "$root"
      return 0
    fi
  fi
  local agy_dir="${AIKIT_ANTIGRAVITY_PLUGINS_DIR:-$HOME/.gemini/config/plugins}"
  if [[ -f "$agy_dir/aikit/scripts/plugin-init.py" ]]; then
    echo "$agy_dir/aikit"
    return 0
  fi
  return 1
}

update_codex() {
  echo "▶ Обновление AIKit для Codex ($WORKSPACE)"
  local kit_root
  kit_root="$(find_codex_kit_root || true)"
  if [[ -z "$kit_root" ]]; then
    echo "AIKit: не найден установленный плагин ядра aikit для Codex." >&2
    exit 1
  fi
  if [[ "$AGENTS_ONLY" -eq 1 ]]; then
    run_py "$kit_root/scripts/plugin-init.py" --runtime codex --refresh-agents --workspace "$WORKSPACE"
  else
    run_py "$kit_root/scripts/update-codex-plugins.py" --workspace "$WORKSPACE"
  fi
}

update_antigravity() {
  echo "▶ Обновление AIKit для Antigravity ($WORKSPACE)"
  local agy_dir="${AIKIT_ANTIGRAVITY_PLUGINS_DIR:-$HOME/.gemini/config/plugins}"
  local core_dir="$agy_dir/aikit"

  if [[ "$AGENTS_ONLY" -eq 0 ]]; then
    local source_root=""
    if [[ -n "${AIKIT_ROOT:-}" && -f "${AIKIT_ROOT}/scripts/install-antigravity-plugins.py" ]]; then
      source_root="$(cd "$AIKIT_ROOT" && pwd)"
    elif [[ -f "$SCRIPT_DIR/install-antigravity-plugins.py" && -f "$SCRIPT_DIR/../VERSION" ]]; then
      source_root="$(cd "$SCRIPT_DIR/.." && pwd)"
    fi

    if [[ -n "$source_root" ]]; then
      echo "Обновление плагинов Antigravity из локального источника ($source_root)..."
      run_py "$source_root/scripts/install-antigravity-plugins.py" --workspace "$WORKSPACE" --target-dir "$agy_dir"
    else
      local repo_url="${AIKIT_REPO_URL:-https://github.com/undef1ned-dev/ai-kit.git}"
      local tmp_dir
      tmp_dir="$(mktemp -d)"
      echo "Загрузка свежей версии AIKit ($repo_url)..."
      if git clone --depth 1 --quiet "$repo_url" "$tmp_dir/ai-kit"; then
        run_py "$tmp_dir/ai-kit/scripts/install-antigravity-plugins.py" --workspace "$WORKSPACE" --target-dir "$agy_dir"
        rm -rf "$tmp_dir"
      else
        rm -rf "$tmp_dir"
        echo "AIKit: не удалось скачать свежую версию из $repo_url" >&2
        exit 1
      fi
    fi
  fi

  if [[ ! -f "$core_dir/scripts/plugin-init.py" ]]; then
    if [[ -f "$SCRIPT_DIR/plugin-init.py" ]]; then
      core_dir="$(cd "$SCRIPT_DIR/.." && pwd)"
    else
      echo "AIKit: плагин ядра Antigravity не найден в $core_dir. Сначала установи плагины." >&2
      exit 1
    fi
  fi

  run_py "$core_dir/scripts/plugin-init.py" --runtime antigravity --refresh-agents --workspace "$WORKSPACE"
  echo "Открой новую сессию Antigravity, чтобы обновлённые плагины и агенты подхватились."
}

for rt in "${TARGET_RUNTIMES[@]}"; do
  case "$rt" in
    codex)
      update_codex
      ;;
    antigravity)
      update_antigravity
      ;;
  esac
done
