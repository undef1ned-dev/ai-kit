#!/usr/bin/env bash
# smoke-plugin.sh — Smoke-тест подключения проекта к AIKit, установленному плагинами
#
# Использование (из любой папки):
#   bash scripts/ci/smoke-plugin.sh <preset> [work-dir]
#
# Что делает (то же, что скилл /aikit:setup):
#   1. Создаёт пустой git-проект со своим текстом в CLAUDE.md, AGENTS.md и .claude/settings.json
#   2. Запускает scripts/plugin-init.py для Claude Code и Codex и проверяет результат
#   3. Запускает повторно с другим набором: блок правил не дублируется, лишние агенты Codex убраны,
#      текст и настройки команды сохранены

set -eo pipefail
# Сообщения скриптов кита с кириллицей печатаются и в консоли Windows
export PYTHONIOENCODING=utf-8

PRESET="${1:-}"
[[ -n "$PRESET" ]] || { echo "Использование: bash scripts/ci/smoke-plugin.sh <preset> [work-dir]" >&2; exit 2; }

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PRESET_FILE="$KIT_ROOT/presets/$PRESET.json"
[[ -f "$PRESET_FILE" ]] || { echo "Пресет не найден: $PRESET_FILE" >&2; exit 2; }

PYTHON_BIN="$(command -v python3 || command -v python)"
WORK_DIR="${2:-$(mktemp -d)}"
PROJECT_DIR="$WORK_DIR/plugin-$PRESET"
rm -rf "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/.claude"

FAILURES=0
pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; FAILURES=$((FAILURES + 1)); }
check() {
  local description="$1"; shift
  if "$@" >/dev/null 2>&1; then pass "$description"; else fail "$description"; fi
}

init() { "$PYTHON_BIN" "$KIT_ROOT/scripts/plugin-init.py" --workspace "$PROJECT_DIR" "$@"; }

# Настройки команды: права кита и свои, без соавторства, маркетплейс aikit и плагины пресета включены
check_claude_settings() {
  "$PYTHON_BIN" - "$PROJECT_DIR/.claude/settings.json" "$PRESET_FILE" <<'PY'
import json, sys
settings = json.load(open(sys.argv[1], encoding="utf-8"))
preset = json.load(open(sys.argv[2], encoding="utf-8"))
assert settings["attribution"] == {"commit": "", "pr": ""}, settings.get("attribution")
allow, deny = settings["permissions"]["allow"], settings["permissions"]["deny"]
assert "Bash(make *)" in allow and any(".env" in rule for rule in deny), settings["permissions"]
assert len(allow) == len(set(allow)), "права дублируются"
assert settings["model"] == "opus", "настройка команды потеряна"
assert settings["extraKnownMarketplaces"]["aikit"]["source"] == {"source": "github", "repo": "undef1ned-dev/ai-kit"}
expected = {f"{name}@aikit" for name in ["aikit", *preset["profiles"], *preset["packs"]]}
assert expected <= {name for name, enabled in settings["enabledPlugins"].items() if enabled}, settings["enabledPlugins"]
PY
}

# Блок правил один, в нём база и все профили пресета, свой текст команды на месте
check_rules() {
  local file="$PROJECT_DIR/$1" profile heading
  [[ "$(grep -c 'BEGIN AIKIT' "$file")" == 1 ]] || { echo "блок AIKit не один в $1" >&2; return 1; }
  grep -qF "Заметки команды" "$file" || { echo "текст команды пропал из $1" >&2; return 1; }
  grep -qF "$(head -1 "$KIT_ROOT/base/CLAUDE.md")" "$file" || return 1
  for profile in $("$PYTHON_BIN" -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"]))' "$PRESET_FILE" | tr -d '\r'); do
    heading="$(head -1 "$KIT_ROOT/profiles/$profile/CLAUDE.md")"
    grep -qF "$heading" "$file" || { echo "в $1 нет профиля $profile" >&2; return 1; }
  done
}

# Агенты Codex: базовые и профилей пресета в TOML, без исходников .md
check_codex_agents() {
  local profile agent
  [[ -f "$PROJECT_DIR/.codex/agents/memory-writer.toml" ]] || return 1
  ! ls "$PROJECT_DIR"/.codex/agents/*.md >/dev/null 2>&1 || return 1
  for profile in $("$PYTHON_BIN" -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"]))' "$PRESET_FILE" | tr -d '\r'); do
    for agent in "$KIT_ROOT"/profiles/"$profile"/agents/*.md; do
      grep -q '^developer_instructions = """' "$PROJECT_DIR/.codex/agents/$(basename "$agent" .md).toml" || return 1
    done
  done
}

echo "▶ Проект → $PROJECT_DIR"
(cd "$PROJECT_DIR" && git init -q)
printf '# Заметки команды\n' > "$PROJECT_DIR/CLAUDE.md"
printf '# Заметки команды\n' > "$PROJECT_DIR/AGENTS.md"
printf '{"model": "opus", "permissions": {"allow": ["Bash(make *)"]}}\n' > "$PROJECT_DIR/.claude/settings.json"

echo "▶ plugin-init.py --runtime claude --preset $PRESET"
init --runtime claude --preset "$PRESET"
check "CLAUDE.md: блок правил базы и профилей, текст команды сохранён" check_rules CLAUDE.md
check ".claude/settings.json: права, маркетплейс aikit, плагины пресета" check_claude_settings
check ".aikit/profiles.json: контракты профилей" test -s "$PROJECT_DIR/.aikit/profiles.json"
check ".aikit/memory/INDEX.md и PRODUCT.md" test -f "$PROJECT_DIR/.aikit/memory/INDEX.md" -a -f "$PROJECT_DIR/PRODUCT.md"
check "агенты и скиллы не копируются в проект — их дают плагины" test ! -e "$PROJECT_DIR/.claude/agents" -a ! -e "$PROJECT_DIR/.claude/skills"

echo "▶ plugin-init.py --runtime codex --preset $PRESET"
init --runtime codex --preset "$PRESET"
check "AGENTS.md: блок правил базы и профилей, текст команды сохранён" check_rules AGENTS.md
check ".codex/agents/: агенты базы и профилей в TOML" check_codex_agents

echo "▶ Повторный запуск с профилем vue-nuxt"
init --runtime claude --preset "$PRESET"
check "повторный запуск: CLAUDE.md не дублирует блок, настройки не дублируются" bash -c "$(declare -f check_rules check_claude_settings); PROJECT_DIR='$PROJECT_DIR' PRESET_FILE='$PRESET_FILE' KIT_ROOT='$KIT_ROOT' PYTHON_BIN='$PYTHON_BIN'; check_rules CLAUDE.md && check_claude_settings"
init --runtime codex --profiles vue-nuxt
check "смена набора: агенты Codex убранных паков удалены" bash -c "test -f '$PROJECT_DIR/.codex/agents/vue-coder.toml' && ! ls '$PROJECT_DIR'/.codex/agents/devops-*.toml"

if [[ "$FAILURES" -gt 0 ]]; then
  echo "✗ Плагины, пресет $PRESET: ошибок — $FAILURES"
  exit 1
fi
echo "✓ Плагины, пресет $PRESET: проект подключён"
