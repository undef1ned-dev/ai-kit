#!/usr/bin/env bash
# update.sh — Умное обновление Claude-конфигов из submodule
#
# Использование (из корня проекта):
#   bash .aikit-config/scripts/update.sh          — интерактивное обновление
#   bash .aikit-config/scripts/update.sh --auto   — авто-обновление без подтверждений
#
# Что делает:
#   1. Тянет последние изменения aikit-config (только если он подключён как submodule)
#   2. Показывает что изменилось с момента установки
#   3. Автоматически обновляет агентов и скиллы (они не кастомизируются)
#   4. Для CLAUDE.md — показывает diff и предлагает обновить

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_ROOT="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(pwd)"
VERSION_FILE="$PROJECT_ROOT/.claude/.config-version"
ROOT_VERSION_FILE="$CONFIG_ROOT/VERSION"
AUTO_MODE=false
[[ "${1:-}" == "--auto" ]] && AUTO_MODE=true

# --- Цвета ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_ok()      { echo -e "${GREEN}✓${NC} $1"; }
log_warn()    { echo -e "${YELLOW}!${NC} $1"; }
log_err()     { echo -e "${RED}✗${NC} $1"; exit 1; }
log_section() { echo -e "\n${CYAN}▶${NC} ${BOLD}$1${NC}"; }
log_info()    { echo -e "  $1"; }

get_repo_version() {
  if [[ -f "$ROOT_VERSION_FILE" ]]; then
    tr -d '[:space:]' < "$ROOT_VERSION_FILE"
  else
    git -C "$CONFIG_ROOT" describe --tags --abbrev=0 2>/dev/null || echo "unversioned"
  fi
}

# shellcheck source=lib/skills.sh
source "$SCRIPT_DIR/lib/skills.sh"
# shellcheck source=lib/mcp.sh
source "$SCRIPT_DIR/lib/mcp.sh"
# shellcheck source=lib/profiles.sh
source "$SCRIPT_DIR/lib/profiles.sh"
# shellcheck source=lib/hooks.sh
source "$SCRIPT_DIR/lib/hooks.sh"

# =============================================================================
# Чтение .config-version
# =============================================================================
if [[ ! -f "$VERSION_FILE" ]]; then
  log_warn ".claude/.config-version не найден — выглядит как первая установка"
  echo ""
  echo "Запусти attach.sh чтобы подключить профиль:"
  echo "  bash .aikit-config/scripts/attach.sh <profile>"
  exit 0
fi

INSTALLED_PROFILES="$(grep '^profiles=' "$VERSION_FILE" | cut -d= -f2)"
INSTALLED_PACKS="$(grep '^packs=' "$VERSION_FILE" | cut -d= -f2)"
INSTALLED_SKILLS_BEFORE="$(grep '^skills=' "$VERSION_FILE" | cut -d= -f2 || true)"
INSTALLED_VERSION="$(grep '^version=' "$VERSION_FILE" | cut -d= -f2)"
INSTALLED_AT="$(grep '^attached_at=' "$VERSION_FILE" | cut -d= -f2)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BOLD}Claude Config Updater${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Профили:  $INSTALLED_PROFILES"
[[ -n "$INSTALLED_PACKS" ]] && echo "  Паки:     $INSTALLED_PACKS"
echo "  Версия:   $INSTALLED_VERSION"
echo "  Дата:     $INSTALLED_AT"
echo ""

# =============================================================================
# Git pull
# =============================================================================
log_section "Обновление aikit-config"

BEFORE_HASH="$(git -C "$CONFIG_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")"
CONFIG_REL="${CONFIG_ROOT#"$PROJECT_ROOT"/}"

# Обновляем кит только если он подключён к проекту как submodule —
# иначе это чей-то рабочий репозиторий, и git pull в нём недопустим
if [[ "$CONFIG_REL" == "$CONFIG_ROOT" ]] || \
   ! git -C "$PROJECT_ROOT" config -f .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null \
     | awk '{print $2}' | grep -qx "$CONFIG_REL"; then
  log_warn "aikit-config не подключён как submodule — пропускаю загрузку, работаю с локальной версией"
elif [[ -n "$(git -C "$CONFIG_ROOT" status --porcelain 2>/dev/null)" ]]; then
  log_warn "В $CONFIG_REL есть локальные изменения — пропускаю загрузку, работаю с локальной версией"
elif git -C "$PROJECT_ROOT" submodule update --remote --quiet -- "$CONFIG_REL" 2>/dev/null; then
  log_ok "Получены последние изменения"
else
  log_warn "Не удалось обновить submodule — работаю с локальной версией"
fi

AFTER_HASH="$(git -C "$CONFIG_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")"
NEW_VERSION="$(get_repo_version)"

# Ничего не изменилось?
if [[ "$BEFORE_HASH" == "$AFTER_HASH" ]]; then
  log_ok "Конфигурация уже актуальна ($NEW_VERSION)"
else
  log_ok "Обновлено: $INSTALLED_VERSION → $NEW_VERSION"
fi

# =============================================================================
# Changelog с момента установки
# =============================================================================
if [[ "$INSTALLED_VERSION" != "unversioned" ]] && \
   [[ "$INSTALLED_VERSION" != "$NEW_VERSION" ]]; then
  log_section "Что изменилось (${INSTALLED_VERSION}..${NEW_VERSION})"
  cd "$CONFIG_ROOT"
  if git rev-parse "$INSTALLED_VERSION" >/dev/null 2>&1; then
    git log --oneline "${INSTALLED_VERSION}..HEAD" 2>/dev/null \
      | sed 's/^/  /' \
      || log_info "(история недоступна)"
  elif [[ -f "$CONFIG_ROOT/CHANGELOG.md" ]] && command -v python3 >/dev/null 2>&1; then
    python3 "$SCRIPT_DIR/changelog_since.py" --from-version "$INSTALLED_VERSION" 2>/dev/null \
      | sed 's/^/  /' \
      || log_info "(CHANGELOG недоступен)"
  else
    log_info "(release notes недоступны — нет git tag range и CHANGELOG fallback)"
  fi
  cd "$PROJECT_ROOT"
elif [[ "$BEFORE_HASH" != "$AFTER_HASH" ]]; then
  log_section "Что изменилось"
  cd "$CONFIG_ROOT"
  git log --oneline "${BEFORE_HASH}..HEAD" 2>/dev/null | sed 's/^/  /' || true
  cd "$PROJECT_ROOT"
fi

# =============================================================================
# Автообновление агентов и скиллов
# =============================================================================
log_section "Обновление агентов и скиллов"

PROFILE_LIST="$(echo "$INSTALLED_PROFILES" | tr '+' ' ')"

AGENTS_DST="$PROJECT_ROOT/.claude/agents"
INSTALLED_SKILLS=""

if [[ -d "$AGENTS_DST" ]]; then
  # Base
  BASE_AGENTS="$CONFIG_ROOT/base/agents"
  [[ -d "$BASE_AGENTS" ]] && cp "$BASE_AGENTS"/*.md "$AGENTS_DST/" 2>/dev/null || true

  # Профили
  # Имена агентов уникальны во всём ките (статическая проверка), поэтому профили копируются как есть
  for p in $PROFILE_LIST; do
    P_AGENTS="$CONFIG_ROOT/profiles/$p/agents"
    [[ -d "$P_AGENTS" ]] && cp "$P_AGENTS"/*.md "$AGENTS_DST/" 2>/dev/null || true
  done

  # Паки
  for pack in $INSTALLED_PACKS; do
    PACK_AGENTS="$CONFIG_ROOT/packs/$pack/agents"
    [[ -d "$PACK_AGENTS" ]] && cp "$PACK_AGENTS"/*.md "$AGENTS_DST/" 2>/dev/null || true
  done

  # Скиллы: убрать прошлую установку (и старые .claude/commands/) и поставить заново
  remove_previous_kit_skills "$PROJECT_ROOT/.claude" "$INSTALLED_SKILLS_BEFORE"
  install_kit_skills "$PROJECT_ROOT/.claude/skills" "$INSTALLED_PACKS"

  AGENT_COUNT="$(ls "$AGENTS_DST"/*.md 2>/dev/null | wc -l | tr -d ' ')"
  SKILL_COUNT="$(echo "$INSTALLED_SKILLS" | wc -w | tr -d ' ')"
  log_ok "Агенты обновлены ($AGENT_COUNT шт)"
  log_ok "Скиллы обновлены ($SKILL_COUNT шт)"
else
  log_warn ".claude/agents/ не найдена — запусти attach.sh"
fi

# =============================================================================
# Smart update CLAUDE.md
# =============================================================================
log_section "CLAUDE.md"

TARGET_CLAUDE="$PROJECT_ROOT/CLAUDE.md"
TMP_NEW_CLAUDE="$(mktemp /tmp/claude-new-XXXXXX.md)"

# Генерируем новую версию
{
  BASE_CLAUDE="$CONFIG_ROOT/base/CLAUDE.md"
  [[ -f "$BASE_CLAUDE" ]] && cat "$BASE_CLAUDE"
  for p in $PROFILE_LIST; do
    P_CLAUDE="$CONFIG_ROOT/profiles/$p/CLAUDE.md"
    if [[ -f "$P_CLAUDE" ]]; then
      echo ""
      echo "---"
      echo ""
      cat "$P_CLAUDE"
    fi
  done
} > "$TMP_NEW_CLAUDE"

if [[ ! -f "$TARGET_CLAUDE" ]]; then
  # CLAUDE.md не существует — просто создаём
  cp "$TMP_NEW_CLAUDE" "$TARGET_CLAUDE"
  log_ok "CLAUDE.md создан"
else
  # Сравниваем с текущим
  DIFF_OUTPUT="$(diff "$TARGET_CLAUDE" "$TMP_NEW_CLAUDE" 2>/dev/null || true)"

  if [[ -z "$DIFF_OUTPUT" ]]; then
    log_ok "CLAUDE.md не изменился"
  else
    DIFF_LINES="$(echo "$DIFF_OUTPUT" | wc -l | tr -d ' ')"
    echo ""
    echo -e "  ${YELLOW}CLAUDE.md изменился${NC} (${DIFF_LINES} строк diff)."
    echo ""
    echo "  Изменения (первые 40 строк):"
    echo "$DIFF_OUTPUT" | head -40 | sed 's/^/    /'
    echo ""

    if $AUTO_MODE; then
      cp "$TMP_NEW_CLAUDE" "$TARGET_CLAUDE"
      log_ok "CLAUDE.md обновлён (--auto режим)"
    else
      printf "  Обновить CLAUDE.md? Твои кастомизации могут быть потеряны. [y/N] "
      read -r REPLY
      if [[ "$REPLY" =~ ^[Yy]$ ]]; then
        # Бэкап текущего
        BACKUP="$PROJECT_ROOT/CLAUDE.md.backup-$(date +%Y%m%d-%H%M%S)"
        cp "$TARGET_CLAUDE" "$BACKUP"
        cp "$TMP_NEW_CLAUDE" "$TARGET_CLAUDE"
        log_ok "CLAUDE.md обновлён (бэкап сохранён в $(basename "$BACKUP"))"
      else
        log_warn "CLAUDE.md оставлен без изменений"
        echo "  Новая версия сохранена в: $TMP_NEW_CLAUDE"
        echo "  Ты можешь сравнить вручную: diff CLAUDE.md $TMP_NEW_CLAUDE"
      fi
    fi
  fi
fi

rm -f "$TMP_NEW_CLAUDE"

# =============================================================================
# MCP-серверы → .mcp.json; settings.json не трогаем — там могут быть правки команды
# =============================================================================
log_section "MCP-серверы"
install_kit_mcp "$INSTALLED_PROFILES" "$INSTALLED_PACKS"
remove_legacy_settings_gitignore
TARGET_SETTINGS="$PROJECT_ROOT/.claude/settings.json"
if [[ -f "$TARGET_SETTINGS" ]]; then
  log_info "settings.json не обновляется автоматически, кроме хуков AIKit: новые permissions из кита — через повторный attach.sh"
fi

# =============================================================================
# Контракты профилей → .aikit/profiles.json; правки команд проекта сохраняются
# =============================================================================
log_section "Контракты профилей"
install_profile_contracts "$INSTALLED_PROFILES"

# =============================================================================
# Хуки → .aikit/hooks/ + hooks в .claude/settings.json; хуки пользователя сохраняются
# =============================================================================
log_section "Хуки"
install_kit_hooks

# =============================================================================
# Обновить версию
# =============================================================================
printf "profiles=%s\npacks=%s\nskills=%s\nversion=%s\nattached_at=%s\n" \
  "$INSTALLED_PROFILES" \
  "$INSTALLED_PACKS" \
  "${INSTALLED_SKILLS:-$INSTALLED_SKILLS_BEFORE}" \
  "$NEW_VERSION" \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$VERSION_FILE"

# =============================================================================
# Итог
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_ok "Обновление завершено! Версия: $NEW_VERSION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
