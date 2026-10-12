#!/usr/bin/env bash
# hooks.sh — хуки AIKit в .claude/settings.json проекта, общая часть attach.sh и update.sh
#
# Подключается через source. Ожидает переменные SCRIPT_DIR, PROJECT_ROOT и функции log_ok, log_warn.

# Поставить .aikit/hooks/aikit_hook.py и прописать его в hooks настроек (хуки пользователя сохраняются)
install_kit_hooks() {
  local installed
  if ! command -v python3 &>/dev/null; then
    log_warn "python3 не найден — хуки не установлены"
    return 0
  fi
  installed="$(python3 "$SCRIPT_DIR/hooks_config.py" claude --workspace "$PROJECT_ROOT")"
  if [[ -n "$installed" ]]; then
    log_ok "Хуки в .claude/settings.json: $installed"
  else
    log_warn "Хуки не установлены — см. сообщение выше"
  fi
}
