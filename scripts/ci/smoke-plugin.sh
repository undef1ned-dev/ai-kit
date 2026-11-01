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
  grep -qF "$(head -1 "$KIT_ROOT/base/RULES.md")" "$file" || return 1
  for profile in $("$PYTHON_BIN" -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"]))' "$PRESET_FILE" | tr -d '\r'); do
    heading="$(head -1 "$KIT_ROOT/profiles/$profile/RULES.md")"
    grep -qF "$heading" "$file" || { echo "в $1 нет профиля $profile" >&2; return 1; }
  done
}

# Агенты Codex: базовые и профилей пресета в TOML, без исходников .md
check_codex_agents() {
  local profile agent
  [[ -f "$PROJECT_DIR/.codex/agents/memory-writer.toml" ]] || return 1
  [[ -z "$(find "$PROJECT_DIR/.codex/agents" -type f -name '*.md' ! -name my-local.md)" ]] || return 1
  for profile in $("$PYTHON_BIN" -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"]))' "$PRESET_FILE" | tr -d '\r'); do
    for agent in "$KIT_ROOT"/profiles/"$profile"/agents/*.md; do
      grep -q '^developer_instructions = ' "$PROJECT_DIR/.codex/agents/$(basename "$agent" .md).toml" || return 1
    done
  done
  # effort is a Claude Code field: Codex gets model_reasoning_effort from native TOML definitions instead
  ! grep -qE '^effort' "$PROJECT_DIR"/.codex/agents/*.toml || return 1
  # Codex reads the project rules from AGENTS.md: no agent sends it to CLAUDE.md
  ! grep -hE '(^|[^/.[:alnum:]_-])CLAUDE\.md' "$PROJECT_DIR"/.codex/agents/*.toml | grep -qv 'AGENTS\.md'
}

# Агенты Antigravity: базовые и профилей пресета в .agents/agents/*.md с subagent: true и model
check_antigravity_agents() {
  local profile agent
  [[ -f "$PROJECT_DIR/.agents/agents/memory-writer.md" ]] || return 1
  for profile in $("$PYTHON_BIN" -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"]))' "$PRESET_FILE" | tr -d '\r'); do
    for agent in "$KIT_ROOT"/profiles/"$profile"/agents/*.md; do
      grep -q '^subagent: true' "$PROJECT_DIR/.agents/agents/$(basename "$agent")" || return 1
    done
  done
  ! grep -qE '^effort' "$PROJECT_DIR"/.agents/agents/*.md || return 1
  ! grep -hE '(^|[^/.[:alnum:]_-])CLAUDE\.md' "$PROJECT_DIR"/.agents/agents/*.md | grep -qv 'AGENTS\.md'
}

echo "▶ Проект → $PROJECT_DIR"
(cd "$PROJECT_DIR" && git init -q)
printf '# Заметки команды\n' > "$PROJECT_DIR/CLAUDE.md"
printf '# Заметки команды\n' > "$PROJECT_DIR/AGENTS.md"
printf '{"model": "opus", "permissions": {"allow": ["Bash(make *)"]}}\n' > "$PROJECT_DIR/.claude/settings.json"

echo "▶ plugin-init.py --runtime claude --preset $PRESET --commit auto"
init --runtime claude --preset "$PRESET" --commit auto
check "CLAUDE.md: блок правил базы и профилей, текст команды сохранён" check_rules CLAUDE.md
check ".claude/settings.json: права, маркетплейс aikit, плагины пресета" check_claude_settings
check ".aikit/profiles.json: контракты профилей" test -s "$PROJECT_DIR/.aikit/profiles.json"
check ".aikit/memory/INDEX.md и PRODUCT.md" test -f "$PROJECT_DIR/.aikit/memory/INDEX.md" -a -f "$PROJECT_DIR/PRODUCT.md"
check ".aikit/settings.json: коммиты без вопроса о сообщении" grep -q '"commit": "auto"' "$PROJECT_DIR/.aikit/settings.json"
check "агенты и скиллы не копируются в проект — их дают плагины" test ! -e "$PROJECT_DIR/.claude/agents" -a ! -e "$PROJECT_DIR/.claude/skills"

# Свой агент команды в .codex/agents: ни конвертация в TOML, ни смена набора его не трогают
mkdir -p "$PROJECT_DIR/.codex/agents"
printf -- '---\nname: "my-local"\ndescription: "Свой агент"\n---\nСвоя роль\n' > "$PROJECT_DIR/.codex/agents/my-local.md"
LOCAL_SUM="$(cksum < "$PROJECT_DIR/.codex/agents/my-local.md")"
check_local_agent() { [[ "$(cksum < "$PROJECT_DIR/.codex/agents/my-local.md")" == "$LOCAL_SUM" ]]; }

echo "▶ plugin-init.py --runtime codex --preset $PRESET"
init --runtime codex --preset "$PRESET"
check "свой агент команды в .codex/agents остался markdown и не изменён" check_local_agent
check "AGENTS.md: блок правил базы и профилей, текст команды сохранён" check_rules AGENTS.md
check "AGENTS.md: собственные инструкции Codex и локальные имена агентов" grep -qF 'Имена из `.aikit/profiles.json` используй без префикса плагина' "$PROJECT_DIR/AGENTS.md"
check ".codex/agents/: агенты базы и профилей в TOML, правила проекта — AGENTS.md" check_codex_agents
check ".aikit/scripts/update-agents.sh: скрипт обновления поставлен в проект" test -f "$PROJECT_DIR/.aikit/scripts/update-agents.sh"
check "запуск без --commit сохраняет выбор команды" grep -q '"commit": "auto"' "$PROJECT_DIR/.aikit/settings.json"
check "plugin-init.json: runtimes хранит оба runtime, запуск в одном не затирает другой" "$PYTHON_BIN" -c "import json,sys; sys.exit(json.load(open(sys.argv[1]))['runtimes'] != ['claude', 'codex'])" "$PROJECT_DIR/.aikit/plugin-init.json"

echo "▶ Повторный запуск с профилем vue-nuxt"
init --runtime claude --preset "$PRESET"
check "повторный запуск: CLAUDE.md не дублирует блок, настройки не дублируются" bash -c "$(declare -f check_rules check_claude_settings); PROJECT_DIR='$PROJECT_DIR' PRESET_FILE='$PRESET_FILE' KIT_ROOT='$KIT_ROOT' PYTHON_BIN='$PYTHON_BIN'; check_rules CLAUDE.md && check_claude_settings"
init --runtime codex --profiles vue-nuxt
check "смена набора: агенты Codex убранных паков удалены" bash -c "test -f '$PROJECT_DIR/.codex/agents/vue-coder.toml' && ! ls '$PROJECT_DIR'/.codex/agents/devops-*.toml"
check "смена набора: свой агент команды не тронут" check_local_agent

echo "▶ plugin-init.py --runtime codex --refresh-agents"
printf '{"agents": {"vue-coder": {"codex": "opus"}}}\n' > "$PROJECT_DIR/.aikit/models.json"
rm -f "$PROJECT_DIR/.codex/agents/vue-coder.toml"
init --runtime codex --refresh-agents >/dev/null
check "refresh-agents: агент пересобран с моделью из .aikit/models.json" grep -q '^model_reasoning_effort = "high"' "$PROJECT_DIR/.codex/agents/vue-coder.toml"
check "refresh-agents: набор профилей прежний, паки смены набора не вернулись" bash -c "test -f '$PROJECT_DIR/.codex/agents/vue-reviewer.toml' && ! ls '$PROJECT_DIR'/.codex/agents/devops-*.toml"
check "refresh-agents: свой агент команды не тронут" check_local_agent
check "refresh-agents: для Claude Code отказ" bash -c "! '$PYTHON_BIN' '$KIT_ROOT/scripts/plugin-init.py' --workspace '$PROJECT_DIR' --runtime claude --refresh-agents >/dev/null 2>&1"

echo "▶ plugin-init.py --runtime antigravity --preset $PRESET"
mkdir -p "$PROJECT_DIR/.agents/agents"
printf -- '---\nname: "my-local"\ndescription: "Свой агент"\nsubagent: true\n---\nСвоя роль\n' > "$PROJECT_DIR/.agents/agents/my-local.md"
LOCAL_AGY_SUM="$(cksum < "$PROJECT_DIR/.agents/agents/my-local.md")"
check_local_agy_agent() { [[ "$(cksum < "$PROJECT_DIR/.agents/agents/my-local.md")" == "$LOCAL_AGY_SUM" ]]; }
init --runtime antigravity --preset "$PRESET"
check "свой агент команды в .agents/agents не изменён" check_local_agy_agent
check "AGENTS.md: инструкции Antigravity и invoke_subagent" grep -qF 'инструмент `invoke_subagent`' "$PROJECT_DIR/AGENTS.md"
check ".agents/agents/: агенты базы и профилей в Markdown с subagent: true" check_antigravity_agents
check "plugin-init.json: runtimes хранит все три runtime" "$PYTHON_BIN" -c "import json,sys; sys.exit(json.load(open(sys.argv[1]))['runtimes'] != ['claude', 'codex', 'antigravity'])" "$PROJECT_DIR/.aikit/plugin-init.json"
init --runtime antigravity --profiles vue-nuxt
check "смена набора Antigravity: агенты убранных паков удалены" bash -c "test -f '$PROJECT_DIR/.agents/agents/vue-coder.md' && ! ls '$PROJECT_DIR'/.agents/agents/devops-*.md 2>/dev/null"
printf '{"agents": {"vue-coder": {"antigravity": "haiku"}}}\n' > "$PROJECT_DIR/.aikit/models.json"
rm -f "$PROJECT_DIR/.agents/agents/vue-coder.md"
init --runtime antigravity --refresh-agents >/dev/null
check "refresh-agents Antigravity: агент пересобран с моделью из .aikit/models.json" grep -q '^model: flash' "$PROJECT_DIR/.agents/agents/vue-coder.md"
check "refresh-agents Antigravity: свой агент команды не тронут" check_local_agy_agent

echo "▶ install-antigravity-plugins.py --workspace"
AGY_PLUGINS_DIR="$WORK_DIR/agy-plugins-$PRESET"
"$PYTHON_BIN" "$KIT_ROOT/scripts/install-antigravity-plugins.py" --workspace "$PROJECT_DIR" --target-dir "$AGY_PLUGINS_DIR" >/dev/null
check "плагин ядра aikit установлен с plugin.json, hooks.json и scripts/plugin-init.py" test -f "$AGY_PLUGINS_DIR/aikit/plugin.json" -a -f "$AGY_PLUGINS_DIR/aikit/hooks.json" -a -f "$AGY_PLUGINS_DIR/aikit/scripts/plugin-init.py"
check "плагин профиля vue-nuxt установлен со скиллами, агентами и MCP" test -f "$AGY_PLUGINS_DIR/vue-nuxt/plugin.json" -a -f "$AGY_PLUGINS_DIR/vue-nuxt/agents/vue-coder.md" -a -f "$AGY_PLUGINS_DIR/vue-nuxt/mcp_config.json"

echo "▶ .aikit/scripts/update-agents.sh"
rm -f "$PROJECT_DIR/.codex/agents/vue-coder.toml" "$PROJECT_DIR/.agents/agents/vue-coder.md"
AIKIT_ROOT="$KIT_ROOT" AIKIT_ANTIGRAVITY_PLUGINS_DIR="$AGY_PLUGINS_DIR" bash "$PROJECT_DIR/.aikit/scripts/update-agents.sh" --agents-only >/dev/null
check "update-agents.sh --agents-only: сам определил codex и antigravity и пересобрал агентов обоих runtime" test -f "$PROJECT_DIR/.codex/agents/vue-coder.toml" -a -f "$PROJECT_DIR/.agents/agents/vue-coder.md"
rm -f "$PROJECT_DIR/.agents/agents/vue-coder.md"
AIKIT_ROOT="$KIT_ROOT" AIKIT_ANTIGRAVITY_PLUGINS_DIR="$AGY_PLUGINS_DIR" bash "$PROJECT_DIR/.aikit/scripts/update-agents.sh" antigravity >/dev/null
check "update-agents.sh antigravity: обновил плагины Antigravity и пересобрал агентов проекта" test -f "$PROJECT_DIR/.agents/agents/vue-coder.md"
"$PYTHON_BIN" "$AGY_PLUGINS_DIR/aikit/scripts/install-antigravity-plugins.py" --workspace "$PROJECT_DIR" --target-dir "$AGY_PLUGINS_DIR" >/dev/null
check "install-antigravity-plugins.py из самого плагина aikit не удаляет хук и runtime" test -f "$AGY_PLUGINS_DIR/aikit/base/antigravity/hooks/aikit_hook.py" -a -f "$AGY_PLUGINS_DIR/aikit/scripts/plugin-init.py" -a -f "$AGY_PLUGINS_DIR/aikit/skills/setup/SKILL.md"

if [[ "$FAILURES" -gt 0 ]]; then
  echo "✗ Плагины, пресет $PRESET: ошибок — $FAILURES"
  exit 1
fi
echo "✓ Плагины, пресет $PRESET: проект подключён"
