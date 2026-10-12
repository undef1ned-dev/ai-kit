#!/usr/bin/env bash
# mcp.sh — MCP-серверы AIKit в .mcp.json проекта, общая часть attach.sh и update.sh
#
# Подключается через source. Ожидает переменные SCRIPT_DIR, PROJECT_ROOT и функции log_ok, log_warn.

# Поставить MCP-серверы профилей и паков в .mcp.json (серверы пользователя сохраняются)
# Использование: install_kit_mcp <profiles a+b> <packs>
install_kit_mcp() {
  local profiles="$1" packs="$2" installed
  if ! command -v python3 &>/dev/null; then
    log_warn "python3 не найден — MCP-серверы не добавлены в .mcp.json"
    return 0
  fi
  installed="$(python3 "$SCRIPT_DIR/mcp_config.py" claude --profiles "$profiles" --packs "$packs" --workspace "$PROJECT_ROOT")"
  log_ok ".mcp.json: ${installed:-нет серверов}"
}

# Прежние версии добавляли .claude/settings.json в .gitignore из-за MCP-путей; теперь настройки общие для команды
remove_legacy_settings_gitignore() {
  local gitignore="$PROJECT_ROOT/.gitignore"
  [[ -f "$gitignore" ]] || return 0
  grep -qx "# Claude Code (локальные настройки MCP — у каждого свои пути)" "$gitignore" || return 0
  awk '
    $0 == "# Claude Code (локальные настройки MCP — у каждого свои пути)" { skip = 1; next }
    skip && $0 == ".claude/settings.json" { skip = 0; next }
    { skip = 0; print }
  ' "$gitignore" > "$gitignore.tmp" && mv "$gitignore.tmp" "$gitignore"
  log_ok ".gitignore: убрано правило для .claude/settings.json — настройки теперь хранятся в git"
}
