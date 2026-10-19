#!/usr/bin/env bash
# run-all.sh — Все проверки CI локально, одной командой
#
# Использование (из любой папки):
#   bash scripts/ci/run-all.sh
#
# Повторяет шаги задачи CI: статические проверки, attach.sh для всех пресетов,
# адаптеры Codex и OpenCode и подключение через плагины для всех пресетов, новый профиль из шаблона.
# Если установлен Claude Code — ещё тесты мода AIKit Deck (claude plugin test, без вызовов модели);
# в CI его нет, поэтому этот шаг только локальный. Не останавливается на первой ошибке.

set -o pipefail

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="$(mktemp -d)"
LOG_DIR="$WORK_DIR/logs"
mkdir -p "$LOG_DIR"
FAILED=()

run_step() {
  local name="$1"; shift
  local log="$LOG_DIR/${name//[^a-zA-Z0-9_-]/_}.log"
  if "$@" > "$log" 2>&1; then
    echo "✓ $name"
  else
    echo "✗ $name (лог: $log)"
    FAILED+=("$name")
  fi
}

run_step "static" bash "$KIT_ROOT/scripts/ci/static-checks.sh"
for preset_file in "$KIT_ROOT"/presets/*.json; do
  preset="$(basename "$preset_file" .json)"
  run_step "attach $preset" bash "$KIT_ROOT/scripts/ci/smoke-attach.sh" "$preset" "$WORK_DIR/attach"
  for adapter in codex opencode; do
    run_step "$adapter $preset" bash "$KIT_ROOT/scripts/ci/smoke-adapter.sh" "$adapter" "$preset" "$WORK_DIR/adapters"
  done
  run_step "plugin $preset" bash "$KIT_ROOT/scripts/ci/smoke-plugin.sh" "$preset" "$WORK_DIR/plugins"
done
run_step "new-profile" bash "$KIT_ROOT/scripts/ci/smoke-new-profile.sh" "$WORK_DIR/new-profile"
if command -v claude &>/dev/null; then
  run_step "deck" bash -c "cd '$KIT_ROOT' && claude plugin test"
else
  echo "– deck: Claude Code не установлен, тесты мода пропущены"
fi

if [[ ${#FAILED[@]} -gt 0 ]]; then
  echo "✗ Не прошло: ${FAILED[*]}"
  exit 1
fi
echo "✓ Все проверки пройдены (временные проекты: $WORK_DIR)"
