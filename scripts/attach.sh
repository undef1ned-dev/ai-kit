#!/usr/bin/env bash
# attach.sh — Подключить один или несколько Claude-профилей к текущему проекту
#
# Использование:
#   bash .aikit-config/scripts/attach.sh <profile>
#   bash .aikit-config/scripts/attach.sh <profile1>+<profile2>
#   bash .aikit-config/scripts/attach.sh <profile> --pack <pack-name>
#   bash .aikit-config/scripts/attach.sh --preset <preset-name>
#
# Примеры:
#   bash .aikit-config/scripts/attach.sh vue-nuxt
#   bash .aikit-config/scripts/attach.sh vue-nuxt+java-spring
#   bash .aikit-config/scripts/attach.sh vue-nuxt --pack devops
#   bash .aikit-config/scripts/attach.sh --preset frontend-team

set -eo pipefail

# --- Аргументы ---
PROFILES_ARG=""
PRESET_NAME=""
PACKS_LIST=""  # пространство-разделённый список паков (bash 3.2 совместимо)
while [[ $# -gt 0 ]]; do
  case "$1" in
    --preset)
      PRESET_NAME="$2"
      shift 2
      ;;
    --pack)
      PACKS_LIST="${PACKS_LIST} $2"
      shift 2
      ;;
    *)
      if [[ -z "$PROFILES_ARG" ]]; then
        PROFILES_ARG="$1"
      fi
      shift
      ;;
  esac
done
PACKS_LIST="${PACKS_LIST# }"  # trim leading space

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_ROOT="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(pwd)"
VERSION_FILE="$PROJECT_ROOT/.claude/.config-version"
ROOT_VERSION_FILE="$CONFIG_ROOT/VERSION"

# --- Цвета ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_ok()      { echo -e "${GREEN}✓${NC} $1"; }
log_warn()    { echo -e "${YELLOW}!${NC} $1"; }
log_err()     { echo -e "${RED}✗${NC} $1"; exit 1; }
log_section() { echo -e "\n${CYAN}▶${NC} $1"; }

if [[ -n "$PRESET_NAME" && -n "$PROFILES_ARG" ]]; then
  log_err "Используй либо <profile>, либо --preset <preset>, но не оба варианта сразу"
fi

read_pack_compatible_profiles() {
  local pack_json="$1"
  [[ -f "$pack_json" ]] || return 0

  if command -v python3 &>/dev/null; then
    python3 -c '
import json, sys
with open(sys.argv[1], encoding="utf-8") as fh:
    data = json.load(fh)
profiles = data.get("compatible_profiles") or []
print("\n".join(profiles))
' "$pack_json" | tr -d '\r'
  fi
}

read_preset_field() {
  local preset_json="$1"
  local field_name="$2"
  [[ -f "$preset_json" ]] || return 0

  if command -v python3 &>/dev/null; then
    python3 -c '
import json, sys
with open(sys.argv[1], encoding="utf-8") as fh:
    data = json.load(fh)
value = data.get(sys.argv[2])
if isinstance(value, list):
    print("\n".join(str(item) for item in value))
elif value is not None:
    print(value)
' "$preset_json" "$field_name" | tr -d '\r'
  fi
}

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
# Валидация
# =============================================================================
if [[ -z "$PROFILES_ARG" ]]; then
  if [[ -n "$PRESET_NAME" ]]; then
    PRESET_JSON="$CONFIG_ROOT/presets/$PRESET_NAME.json"
    [[ -f "$PRESET_JSON" ]] || log_err "Пресет '$PRESET_NAME' не найден в $CONFIG_ROOT/presets/"
    PROFILES_ARG="$(read_preset_field "$PRESET_JSON" profiles | paste -sd+ -)"
    PRESET_PACKS="$(read_preset_field "$PRESET_JSON" packs | paste -sd' ' -)"
    if [[ -n "$PRESET_PACKS" ]]; then
      PACKS_LIST="${PRESET_PACKS}${PACKS_LIST:+ $PACKS_LIST}"
    fi
    PACKS_LIST="$(printf '%s\n' "$PACKS_LIST" | tr ' ' '\n' | awk 'NF && !seen[$0]++' | paste -sd' ' -)"
  else
    echo "Доступные профили:"
    ls "$CONFIG_ROOT/profiles/" 2>/dev/null | sed 's/^/  - /' || echo "  (нет профилей)"
    echo ""
    echo "Доступные пресеты:"
    ls "$CONFIG_ROOT/presets/" 2>/dev/null | sed 's/\.json$//' | sed 's/^/  - /' || echo "  (нет пресетов)"
    echo ""
    log_err "Укажи профиль: bash attach.sh <profile>  или  bash attach.sh <profile1>+<profile2>  или  bash attach.sh --preset <preset>"
  fi
fi

# Разбиваем profile1+profile2 в пространство-разделённый список
PROFILE_LIST="$(echo "$PROFILES_ARG" | tr '+' ' ')"
PROFILE_COUNT="$(echo "$PROFILE_LIST" | wc -w | tr -d ' ')"

for p in $PROFILE_LIST; do
  [[ -d "$CONFIG_ROOT/profiles/$p" ]] || log_err "Профиль '$p' не найден в $CONFIG_ROOT/profiles/"
done

for pack in $PACKS_LIST; do
  [[ -d "$CONFIG_ROOT/packs/$pack" ]] || log_err "Пак '$pack' не найден в $CONFIG_ROOT/packs/"

  PACK_JSON="$CONFIG_ROOT/packs/$pack/pack.json"
  COMPATIBLE_PROFILES="$(read_pack_compatible_profiles "$PACK_JSON")"
  [[ -z "$COMPATIBLE_PROFILES" ]] && continue

  # В мульти-профиле пак достаточно совместить хотя бы с одним профилем (например, ai-пак для backend в fullstack)
  PACK_MATCHED=false
  for p in $PROFILE_LIST; do
    echo "$COMPATIBLE_PROFILES" | grep -qx "$p" 2>/dev/null && PACK_MATCHED=true
  done
  $PACK_MATCHED || log_err "Пак '$pack' не совместим ни с одним из профилей: $PROFILES_ARG"
done

MULTI_PROFILE=false
[[ "$PROFILE_COUNT" -gt 1 ]] && MULTI_PROFILE=true

echo ""
echo "Подключаю: $PROFILES_ARG"
echo "Проект: $PROJECT_ROOT"
[[ -n "$PRESET_NAME" ]] && echo "Пресет: $PRESET_NAME"
[[ -n "$PACKS_LIST" ]] && echo "Паки: $PACKS_LIST"
echo ""

# =============================================================================
# Создать .claude/
# =============================================================================
mkdir -p "$PROJECT_ROOT/.claude/agents"

# =============================================================================
# CLAUDE.md: base + все профили
# =============================================================================
log_section "CLAUDE.md"

TARGET_CLAUDE="$PROJECT_ROOT/CLAUDE.md"
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
} > "$TARGET_CLAUDE"

log_ok "CLAUDE.md создан (base + $PROFILES_ARG)"

# =============================================================================
# settings.json: base + все профили + паки через jq reduce
# =============================================================================
log_section "settings.json"

TARGET_SETTINGS="$PROJECT_ROOT/.claude/settings.json"
SETTINGS_FILES=""
BASE_SETTINGS="$CONFIG_ROOT/base/settings.json"
[[ -f "$BASE_SETTINGS" ]] && SETTINGS_FILES="$BASE_SETTINGS"

for p in $PROFILE_LIST; do
  P_SETTINGS="$CONFIG_ROOT/profiles/$p/settings.json"
  [[ -f "$P_SETTINGS" ]] && SETTINGS_FILES="$SETTINGS_FILES $P_SETTINGS"
done

for pack in $PACKS_LIST; do
  PACK_SETTINGS="$CONFIG_ROOT/packs/$pack/settings.json"
  [[ -f "$PACK_SETTINGS" ]] && SETTINGS_FILES="$SETTINGS_FILES $PACK_SETTINGS"
done
SETTINGS_FILES="${SETTINGS_FILES# }"

if [[ -n "$SETTINGS_FILES" ]] && command -v jq &>/dev/null; then
  FILES_COUNT="$(echo "$SETTINGS_FILES" | wc -w | tr -d ' ')"
  MERGE_CMD='reduce .[] as $l ({}; . * $l
    | .permissions.allow = ([(.permissions.allow // []), ($l.permissions.allow // [])] | add | unique)
    | .permissions.deny  = ([(.permissions.deny  // []), ($l.permissions.deny  // [])] | add | unique)
  )'
  # shellcheck disable=SC2086
  jq -s "$MERGE_CMD" $SETTINGS_FILES > "$TARGET_SETTINGS" 2>/dev/null \
    || { log_warn "jq merge не удался, копирую последний профиль"; \
         LAST_P="$(echo "$PROFILE_LIST" | awk '{print $NF}')"; \
         cp "$CONFIG_ROOT/profiles/$LAST_P/settings.json" "$TARGET_SETTINGS" 2>/dev/null || true; }
  log_ok ".claude/settings.json создан (merged $FILES_COUNT файлов)"
elif [[ -n "$SETTINGS_FILES" ]] && command -v python3 &>/dev/null; then
  # Та же логика, что и в jq-ветке: deep merge, allow/deny объединяются без дублей
  FILES_COUNT="$(echo "$SETTINGS_FILES" | wc -w | tr -d ' ')"
  # shellcheck disable=SC2086
  python3 -c '
import json, sys

def deep_merge(base, layer):
    for key, value in layer.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base

merged = {}
for path in sys.argv[2:]:
    with open(path, encoding="utf-8") as fh:
        layer = json.load(fh)
    perms = {k: list(merged.get("permissions", {}).get(k, [])) for k in ("allow", "deny")}
    deep_merge(merged, layer)
    for key, items in perms.items():
        for item in layer.get("permissions", {}).get(key, []):
            if item not in items:
                items.append(item)
        if items:
            merged.setdefault("permissions", {})[key] = sorted(items)

with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as fh:
    json.dump(merged, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
' "$TARGET_SETTINGS" $SETTINGS_FILES
  log_ok ".claude/settings.json создан (merged $FILES_COUNT файлов, python)"
elif [[ -n "$SETTINGS_FILES" ]]; then
  log_warn "Нет ни jq, ни python3 — копирую только последний профиль"
  LAST_P="$(echo "$PROFILE_LIST" | awk '{print $NF}')"
  cp "$CONFIG_ROOT/profiles/$LAST_P/settings.json" "$TARGET_SETTINGS" 2>/dev/null || true
  log_ok ".claude/settings.json создан (только $LAST_P)"
else
  log_warn "settings.json не найден"
fi

# =============================================================================
# MCP-серверы → .mcp.json
# =============================================================================
log_section "MCP-серверы"
install_kit_mcp "$PROFILES_ARG" "$PACKS_LIST"

# =============================================================================
# Контракты профилей → .aikit/profiles.json
# =============================================================================
log_section "Контракты профилей"
install_profile_contracts "$PROFILES_ARG"

# =============================================================================
# Хуки → .aikit/hooks/ + hooks в .claude/settings.json
# =============================================================================
log_section "Хуки"
install_kit_hooks

# =============================================================================
# Скиллы: base + профили + паки
# =============================================================================
log_section "Скиллы"

PREVIOUS_SKILLS="$( [[ -f "$VERSION_FILE" ]] && grep '^skills=' "$VERSION_FILE" | cut -d= -f2 || true)"
remove_previous_kit_skills "$PROJECT_ROOT/.claude" "$PREVIOUS_SKILLS"
install_kit_skills "$PROJECT_ROOT/.claude/skills" "$PACKS_LIST"
SKILL_COUNT="$(echo "$INSTALLED_SKILLS" | wc -w | tr -d ' ')"
log_ok "Скиллы в .claude/skills/ ($SKILL_COUNT шт)"

# =============================================================================
# Субагенты: base + профили + паки
# =============================================================================
log_section "Субагенты"

AGENTS_DST="$PROJECT_ROOT/.claude/agents"
BASE_AGENTS="$CONFIG_ROOT/base/agents"
[[ -d "$BASE_AGENTS" ]] && cp "$BASE_AGENTS"/*.md "$AGENTS_DST/" 2>/dev/null || true

# Имена агентов уникальны во всём ките (статическая проверка), поэтому профили копируются как есть
for p in $PROFILE_LIST; do
  P_AGENTS="$CONFIG_ROOT/profiles/$p/agents"
  [[ -d "$P_AGENTS" ]] && cp "$P_AGENTS"/*.md "$AGENTS_DST/" 2>/dev/null || true
done

for pack in $PACKS_LIST; do
  PACK_AGENTS="$CONFIG_ROOT/packs/$pack/agents"
  [[ -d "$PACK_AGENTS" ]] && cp "$PACK_AGENTS"/*.md "$AGENTS_DST/" 2>/dev/null || true
done

AGENT_COUNT="$(ls "$AGENTS_DST"/*.md 2>/dev/null | wc -l | tr -d ' ')"
log_ok "Субагенты в .claude/agents/ ($AGENT_COUNT шт)"
apply_agent_models

# =============================================================================
# PRODUCT.md — шаблон если нет
# =============================================================================
PRODUCT_TEMPLATE="$CONFIG_ROOT/base/PRODUCT.md"
PRODUCT_TARGET="$PROJECT_ROOT/PRODUCT.md"
if [[ ! -f "$PRODUCT_TARGET" ]] && [[ -f "$PRODUCT_TEMPLATE" ]]; then
  cp "$PRODUCT_TEMPLATE" "$PRODUCT_TARGET"
  log_ok "PRODUCT.md создан (заполни информацию о продукте)"
fi

# =============================================================================
# .aikit/memory — командная память проекта (решения, паттерны, коррекции агентов)
# =============================================================================
CANONICAL_MEMORY_DIR="$PROJECT_ROOT/.aikit/memory"
LEGACY_MEMORY_DIR="$PROJECT_ROOT/.claude/memory"
MEMORY_TEMPLATE="$CONFIG_ROOT/base/memory/INDEX.md"

if [[ -d "$CANONICAL_MEMORY_DIR" ]]; then
  log_ok ".aikit/memory/ уже есть — оставляю как есть"
elif [[ -d "$LEGACY_MEMORY_DIR" ]]; then
  mkdir -p "$CANONICAL_MEMORY_DIR"
  cp -R "$LEGACY_MEMORY_DIR"/. "$CANONICAL_MEMORY_DIR"/
  log_ok ".aikit/memory/ перенесена из .claude/memory/ прежних версий"
else
  mkdir -p "$CANONICAL_MEMORY_DIR/decisions" "$CANONICAL_MEMORY_DIR/patterns" "$CANONICAL_MEMORY_DIR/corrections" "$CANONICAL_MEMORY_DIR/features"
  touch "$CANONICAL_MEMORY_DIR/decisions/.gitkeep" "$CANONICAL_MEMORY_DIR/patterns/.gitkeep" "$CANONICAL_MEMORY_DIR/corrections/.gitkeep" "$CANONICAL_MEMORY_DIR/features/.gitkeep"
  [[ -f "$MEMORY_TEMPLATE" ]] && cp "$MEMORY_TEMPLATE" "$CANONICAL_MEMORY_DIR/INDEX.md"
  log_ok ".aikit/memory/ создана"
fi
if [[ -d "$LEGACY_MEMORY_DIR" ]]; then
  log_warn ".claude/memory/ больше не используется — агенты читают .aikit/memory/. Сверь, что всё перенесено, и удали папку"
fi

# =============================================================================
# .gitignore
# =============================================================================
GITIGNORE="$PROJECT_ROOT/.gitignore"
remove_legacy_settings_gitignore
if [[ -f "$GITIGNORE" ]]; then
  if grep -q "\.aikit/memory" "$GITIGNORE" 2>/dev/null; then
    log_warn "ВНИМАНИЕ: .aikit/memory/ найдена в .gitignore — командная память должна храниться в git"
  fi
fi

# =============================================================================
# Версия конфигурации
# =============================================================================
CURRENT_TAG="$(get_repo_version)"
printf "profiles=%s\npacks=%s\nskills=%s\nversion=%s\nattached_at=%s\n" \
  "$PROFILES_ARG" \
  "$PACKS_LIST" \
  "$INSTALLED_SKILLS" \
  "$CURRENT_TAG" \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$VERSION_FILE"
log_ok ".claude/.config-version записан ($CURRENT_TAG)"

# =============================================================================
# Итог
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_ok "Профиль(и) '$PROFILES_ARG' подключён(ы)!"
echo ""
echo "Созданные файлы:"
echo "  CLAUDE.md                  — правила для Claude"
echo "  .claude/settings.json      — permissions и настройки (хранится в git)"
echo "  .mcp.json                  — MCP-серверы (хранится в git)"
echo "  .aikit/hooks/aikit_hook.py — хуки: правила коммитов, веток и секретов, линтер, тесты, память"
echo "  .aikit/profiles.json       — контракты профилей: агенты по ролям, папка и команды (root и команды можно править)"
printf "  .claude/skills/            — скиллы: /name или автоматически по описанию (%s шт)\n" "$SKILL_COUNT"
printf "  .claude/agents/            — субагенты (%s шт)\n" "$AGENT_COUNT"
echo "  PRODUCT.md                 — заполни информацию о продукте"
echo "  .aikit/memory/             — командная память: решения, паттерны, коррекции агентов (хранится в git)"
echo "  .claude/.config-version    — версия конфигурации"
echo ""
echo "Следующие шаги:"
echo "  1. Заполни PRODUCT.md — агенты читают его для контекста"
echo "  2. MCP: Figma и Sentry попросят войти (OAuth) при первом вызове"
echo "  3. После первой содержательной задачи запусти /capture-memory"
if $MULTI_PROFILE; then
  echo ""
  echo "Подсказка мульти-профиль:"
  echo "  /implement-feature и /workflow выбирают профиль по задаче; агенты и папки профилей — в .aikit/profiles.json"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
