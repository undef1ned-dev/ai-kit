#!/usr/bin/env bash
# profiles.sh — контракты профилей в .aikit/profiles.json проекта, общая часть attach.sh и update.sh
#
# Подключается через source. Ожидает переменные SCRIPT_DIR, PROJECT_ROOT и функции log_ok, log_warn.

# Собрать контракты профилей (агенты по ролям, команды) в .aikit/profiles.json; правки команд проекта сохраняются
# Использование: install_profile_contracts <profiles a+b>
# Модели агентов: уровни из frontmatter и переопределения проекта (.aikit/models.json)
apply_agent_models() {
  command -v python3 &>/dev/null || return 0
  log_ok "$(python3 "$SCRIPT_DIR/agent_models.py" apply --runtime claude --workspace "$PROJECT_ROOT")"
}

install_profile_contracts() {
  local profiles="$1" installed
  if ! command -v python3 &>/dev/null; then
    log_warn "python3 не найден — .aikit/profiles.json не обновлён"
    return 0
  fi
  installed="$(python3 "$SCRIPT_DIR/profile_contract.py" --profiles "$profiles" --workspace "$PROJECT_ROOT")"
  log_ok ".aikit/profiles.json: ${installed:-нет профилей}"
}
