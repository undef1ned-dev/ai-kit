#!/usr/bin/env bash
# static-checks.sh — Статические проверки репозитория AIKit
#
# Использование (из корня репозитория):
#   bash scripts/ci/static-checks.sh
#
# Что проверяет (только файлы под git):
#   1. Синтаксис всех *.sh (bash -n) и грубые ошибки через shellcheck, если он установлен
#   2. Синтаксис всех *.py (компиляция без записи __pycache__)
#   3. Корректность всех *.json

set -eo pipefail

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$KIT_ROOT"
PYTHON_BIN="$(command -v python3 || command -v python)"
FAILURES=0

list_files() { git ls-files -z -- "$1" | tr '\0' '\n' | tr -d '\r'; }

echo "▶ bash -n"
while IFS= read -r f; do
  [[ -n "$f" ]] || continue
  bash -n "$f" || { echo "  ✗ $f"; FAILURES=$((FAILURES + 1)); }
done < <(list_files '*.sh')

if command -v shellcheck >/dev/null 2>&1; then
  echo "▶ shellcheck (только ошибки)"
  list_files '*.sh' | tr '\n' '\0' | xargs -0 shellcheck --severity=error || FAILURES=$((FAILURES + 1))
else
  echo "! shellcheck не установлен — пропускаю"
fi

echo "▶ Python: синтаксис"
list_files '*.py' | "$PYTHON_BIN" -c '
import sys
failed = 0
for path in filter(None, (line.strip() for line in sys.stdin)):
    try:
        with open(path, encoding="utf-8") as f:
            compile(f.read(), path, "exec")
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"  ✗ {path}: {e}")
        failed += 1
sys.exit(1 if failed else 0)
' || FAILURES=$((FAILURES + 1))

echo "▶ JSON: синтаксис"
list_files '*.json' | "$PYTHON_BIN" -c '
import json, sys
failed = 0
for path in filter(None, (line.strip() for line in sys.stdin)):
    try:
        with open(path, encoding="utf-8") as f:
            json.load(f)
    except (ValueError, UnicodeDecodeError) as e:
        print(f"  ✗ {path}: {e}")
        failed += 1
sys.exit(1 if failed else 0)
' || FAILURES=$((FAILURES + 1))

if [[ "$FAILURES" -gt 0 ]]; then
  echo "✗ Статические проверки: ошибок — $FAILURES"
  exit 1
fi
echo "✓ Статические проверки пройдены"
