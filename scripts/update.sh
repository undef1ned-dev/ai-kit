#!/usr/bin/env bash
# update.sh — Умное обновление Claude-конфигов из submodule
#
# Использование (из корня проекта):
#   bash .aikit-config/scripts/update.sh          — интерактивное обновление
#   bash .aikit-config/scripts/update.sh --auto   — авто-обновление без подтверждений
#
# Что делает:
#   1. Тянет последние изменения из aikit-config
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

profile_prefix() {
  echo "$1" | sed 's/python-//; s/-[a-z]*$//'
}

find_conflicts() {
  local subdir="$1"
  local all_files=""
  for p in $PROFILE_LIST; do
    local dir="$CONFIG_ROOT/profiles/$p/$subdir"
    if [[ -d "$dir" ]]; then
      for f in "$dir"/*.md; do
        [[ -f "$f" ]] && all_files="${all_files}$(basename "$f")\n"
      done
    fi
  done
  printf "%b" "$all_files" | sort | uniq -d
}

copy_profile_files() {
  local subdir="$1"
  local dst="$2"
  local conflicts
  conflicts="$(find_conflicts "$subdir")"

  for p in $PROFILE_LIST; do
    local src="$CONFIG_ROOT/profiles/$p/$subdir"
    [[ -d "$src" ]] || continue
    local prefix
    prefix="$(profile_prefix "$p")"

    for f in "$src"/*.md; do
      [[ -f "$f" ]] || continue
      local fname
      fname="$(basename "$f")"

      if echo "$conflicts" | grep -qx "$fname" 2>/dev/null; then
        cp "$f" "$dst/${prefix}-${fname}"
      else
        cp "$f" "$dst/$fname"
      fi
    done
  done
}

expand_skill_templates() {
  local dst="$1"
  local tmpl_dir="$CONFIG_ROOT/base/skills/templates"
  [[ -d "$tmpl_dir" ]] || return 0
  command -v python3 &>/dev/null || { log_warn "python3 не найден — шаблонные скиллы не расширены"; return 0; }

  local expanded=0
  for f in "$dst"/*.md; do
    [[ -f "$f" ]] || continue
    grep -q '^template:' "$f" 2>/dev/null || continue
    python3 "$SCRIPT_DIR/expand-template.py" "$f" "$tmpl_dir" \
      && expanded=$((expanded + 1))
  done
  [[ "$expanded" -gt 0 ]] && log_ok "Расширено $expanded шаблонных скилла(ов)"
}

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

cd "$CONFIG_ROOT"
BEFORE_HASH="$(git rev-parse HEAD 2>/dev/null || echo "unknown")"
git pull origin main --quiet 2>/dev/null && log_ok "Получены последние изменения" \
  || { log_warn "git pull не удался — работаю с локальной версией"; }
AFTER_HASH="$(git rev-parse HEAD 2>/dev/null || echo "unknown")"
NEW_VERSION="$(get_repo_version)"

cd "$PROJECT_ROOT"

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
SKILLS_DST="$PROJECT_ROOT/.claude/commands"

if [[ -d "$AGENTS_DST" ]] || [[ -d "$SKILLS_DST" ]]; then
  # Base
  BASE_AGENTS="$CONFIG_ROOT/base/agents"
  BASE_SKILLS="$CONFIG_ROOT/base/skills"
  [[ -d "$BASE_AGENTS" ]] && cp "$BASE_AGENTS"/*.md "$AGENTS_DST/" 2>/dev/null || true
  [[ -d "$BASE_SKILLS" ]] && cp "$BASE_SKILLS"/*.md "$SKILLS_DST/" 2>/dev/null || true

  # Skills в формате SKILL.md: base/skills/<name>/SKILL.md → .claude/skills/<name>/
  for d in "$BASE_SKILLS"/*/; do
    [[ -f "${d}SKILL.md" ]] || continue
    mkdir -p "$PROJECT_ROOT/.claude/skills"
    cp -R "${d%/}" "$PROJECT_ROOT/.claude/skills/"
  done

  # Профили
  PROFILE_COUNT="$(echo "$PROFILE_LIST" | wc -w | tr -d ' ')"
  MULTI_PROFILE=false
  [[ "$PROFILE_COUNT" -gt 1 ]] && MULTI_PROFILE=true

  if $MULTI_PROFILE; then
    copy_profile_files "agents" "$AGENTS_DST"
    copy_profile_files "skills" "$SKILLS_DST"
  else
    for p in $PROFILE_LIST; do
      P_AGENTS="$CONFIG_ROOT/profiles/$p/agents"
      P_SKILLS="$CONFIG_ROOT/profiles/$p/skills"
      [[ -d "$P_AGENTS" ]] && cp "$P_AGENTS"/*.md "$AGENTS_DST/" 2>/dev/null || true
      [[ -d "$P_SKILLS" ]] && cp "$P_SKILLS"/*.md "$SKILLS_DST/" 2>/dev/null || true
    done
  fi

  # Паки
  for pack in $INSTALLED_PACKS; do
    PACK_AGENTS="$CONFIG_ROOT/packs/$pack/agents"
    PACK_SKILLS="$CONFIG_ROOT/packs/$pack/skills"
    [[ -d "$PACK_AGENTS" ]] && cp "$PACK_AGENTS"/*.md "$AGENTS_DST/" 2>/dev/null || true
    [[ -d "$PACK_SKILLS" ]] && cp "$PACK_SKILLS"/*.md "$SKILLS_DST/" 2>/dev/null || true
  done

  expand_skill_templates "$SKILLS_DST"

  AGENT_COUNT="$(ls "$AGENTS_DST"/*.md 2>/dev/null | wc -l | tr -d ' ')"
  SKILL_COUNT="$(ls "$SKILLS_DST"/*.md 2>/dev/null | wc -l | tr -d ' ')"
  log_ok "Агенты обновлены ($AGENT_COUNT шт)"
  log_ok "Скиллы обновлены ($SKILL_COUNT шт)"
else
  log_warn ".claude/agents/ или .claude/commands/ не найдены — запусти attach.sh"
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
# settings.json — предупреждение (не обновляем автоматически)
# =============================================================================
TARGET_SETTINGS="$PROJECT_ROOT/.claude/settings.json"
if [[ -f "$TARGET_SETTINGS" ]]; then
  log_section "settings.json"
  log_warn "settings.json не обновляется автоматически"
  log_info "Он содержит локальные пути MCP-серверов, у каждого разработчика свои."
  log_info "Если добавлены новые MCP-серверы — перезапусти attach.sh."
fi

# =============================================================================
# Обновить версию
# =============================================================================
printf "profiles=%s\npacks=%s\nversion=%s\nattached_at=%s\n" \
  "$INSTALLED_PROFILES" \
  "$INSTALLED_PACKS" \
  "$NEW_VERSION" \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$VERSION_FILE"

# =============================================================================
# Итог
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_ok "Обновление завершено! Версия: $NEW_VERSION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
