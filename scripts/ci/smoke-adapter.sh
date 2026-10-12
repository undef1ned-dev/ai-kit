#!/usr/bin/env bash
# smoke-adapter.sh — Smoke-тест установки AIKit через адаптер (Codex, OpenCode)
#
# Использование (из любой папки):
#   bash scripts/ci/smoke-adapter.sh <adapter> <preset> [work-dir]
#
# Что делает:
#   1. Ставит пресет через install-adapter-package.py в проект, где уже есть свой AGENTS.md
#   2. Проверяет файлы, которые реально читает runtime (AGENTS.md, .agents/skills, агенты runtime)
#   3. Запускает update-adapter-package.py и проверяет, что установка не сломалась и старые файлы убраны
#
# HOME подменяется временной папкой: установка не должна ничего писать в домашнюю папку пользователя.

set -eo pipefail

ADAPTER="${1:-}"
PRESET="${2:-}"
[[ -n "$ADAPTER" && -n "$PRESET" ]] || { echo "Использование: bash scripts/ci/smoke-adapter.sh <adapter> <preset> [work-dir]" >&2; exit 2; }

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[[ -f "$KIT_ROOT/adapters/$ADAPTER/adapter.manifest.json" ]] || { echo "Адаптер не найден: $ADAPTER" >&2; exit 2; }
[[ -f "$KIT_ROOT/presets/$PRESET.json" ]] || { echo "Пресет не найден: $PRESET" >&2; exit 2; }

PYTHON_BIN="$(command -v python3 || command -v python)"
WORK_DIR="${3:-$(mktemp -d)}"
PROJECT_DIR="$WORK_DIR/$ADAPTER-$PRESET"
FAKE_HOME="$WORK_DIR/$ADAPTER-$PRESET-home"
mkdir -p "$PROJECT_DIR" "$FAKE_HOME"
USER_RULES_LINE="Правило пользователя: не трогать этот текст"
printf '# Мои правила\n\n%s\n' "$USER_RULES_LINE" > "$PROJECT_DIR/AGENTS.md"

FAILURES=0
pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; FAILURES=$((FAILURES + 1)); }
check() {
  local description="$1"; shift
  if "$@" >/dev/null 2>&1; then pass "$description"; else fail "$description"; fi
}

count_files() { find "$1" -type f -name "$2" 2>/dev/null | wc -l | tr -d ' '; }

run_installer() {
  local script="$1" log="$2"
  # Python takes the home folder from USERPROFILE on Windows and from HOME elsewhere
  HOME="$FAKE_HOME" USERPROFILE="$FAKE_HOME" \
    "$PYTHON_BIN" "$KIT_ROOT/scripts/$script" "$ADAPTER" --preset "$PRESET" --workspace "$PROJECT_DIR" > "$log" 2>&1
}

# AGENTS.md: ровно один блок AIKit с правилами, текст пользователя на месте
check_agents_md() {
  local file="$PROJECT_DIR/AGENTS.md"
  [[ "$(grep -c '<!-- BEGIN AIKIT' "$file")" == 1 && "$(grep -c '<!-- END AIKIT -->' "$file")" == 1 ]] || return 1
  grep -qF "$USER_RULES_LINE" "$file" || return 1
  grep -qF "$(head -1 "$KIT_ROOT/base/CLAUDE.md")" "$file"
}

# .agents/skills/<name>/SKILL.md: frontmatter с name (совпадает с папкой) и description — требование Codex и OpenCode
check_native_skills() {
  "$PYTHON_BIN" - "$PROJECT_DIR/.agents/skills" <<'PY'
import json, pathlib, re, sys
skills = list(pathlib.Path(sys.argv[1]).glob("*/SKILL.md"))
assert skills, "нет скиллов"
for path in skills:
    match = re.match(r"---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    assert match, f"нет frontmatter: {path}"
    fields = dict(re.findall(r'(?m)^(\w+):\s*(.+)$', match.group(1)))
    assert json.loads(fields.get("name", '""')) == path.parent.name, f"name не совпадает с папкой: {path}"
    assert json.loads(fields.get("description", '""')).strip(), f"нет description: {path}"
PY
}

# $ARGUMENTS подставляет только Claude Code, а template: означает нераскрытый шаблон
check_no_raw_placeholders() {
  ! grep -rlE '[$]ARGUMENTS|^template:' "$PROJECT_DIR/.agents/skills"
}

# Агенты Codex — валидный TOML с обязательными полями; config.toml, если есть, тоже валиден
check_codex_agents() {
  "$PYTHON_BIN" - "$PROJECT_DIR/.codex" <<'PY'
import pathlib, sys, tomllib
root = pathlib.Path(sys.argv[1])
if (root / "config.toml").exists():
    with open(root / "config.toml", "rb") as f:
        tomllib.load(f)
agents = list((root / "agents").glob("*.toml"))
assert agents, "нет агентов"
for path in agents:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    missing = {"name", "description", "developer_instructions"} - data.keys()
    assert not missing, f"{path.name}: нет полей {missing}"
PY
}

# Агенты OpenCode — markdown с description и mode: subagent
check_opencode_agents() {
  local f found=0
  for f in "$PROJECT_DIR"/.opencode/agents/*.md; do
    [[ -f "$f" ]] || continue
    found=1
    grep -q '^description: "..*"' "$f" && grep -q '^mode: "subagent"' "$f" || { echo "неверный агент: $f" >&2; return 1; }
  done
  [[ "$found" == 1 ]]
}

check_runtime_files() {
  local stage="$1"
  check "AGENTS.md: блок AIKit один, правила пользователя сохранены$stage" check_agents_md
  check "скиллы в .agents/skills: name = папка, есть description$stage" check_native_skills
  check "скилл git-commit установлен$stage" test -f "$PROJECT_DIR/.agents/skills/git-commit/SKILL.md"
  check "в скиллах нет \$ARGUMENTS и нераскрытых шаблонов$stage" check_no_raw_placeholders
  case "$ADAPTER" in
    codex)
      check "скилл workflow не вызывается автоматически (agents/openai.yaml)$stage" grep -q 'allow_implicit_invocation: false' "$PROJECT_DIR/.agents/skills/workflow/agents/openai.yaml"
      check "агенты Codex — валидный TOML$stage" check_codex_agents
      check "нет markdown-дублей агентов в .codex/agents$stage" test "$(count_files "$PROJECT_DIR/.codex/agents" '*.md')" -eq 0
      check "нет устаревших .codex/commands и .codex/skills$stage" test ! -e "$PROJECT_DIR/.codex/commands" -a ! -e "$PROJECT_DIR/.codex/skills"
      ;;
    opencode)
      check "агенты OpenCode с description и mode: subagent$stage" check_opencode_agents
      ;;
  esac
  check "в домашнюю папку ничего не записано$stage" test -z "$(ls -A "$FAKE_HOME")"
}

echo "▶ Адаптер $ADAPTER, пресет $PRESET → $PROJECT_DIR"

echo "▶ install-adapter-package.py"
INSTALL_LOG="$WORK_DIR/$ADAPTER-$PRESET-install.log"
run_installer install-adapter-package.py "$INSTALL_LOG" || { cat "$INSTALL_LOG"; echo "✗ Установка завершилась с ошибкой"; exit 1; }

check "агенты кита установлены (.aikit/agents)" test "$(count_files "$PROJECT_DIR/.aikit/agents" '*.md')" -gt 0
check "память проекта создана" test -d "$PROJECT_DIR/.aikit/memory"
check "нет нераскрытых шаблонов {{...}}" bash -c "! grep -rlF '{{' '$PROJECT_DIR/.aikit/agents' '$PROJECT_DIR/.agents/skills' '$PROJECT_DIR/AGENTS.md'"
check_runtime_files ""

# Файлы, которые ставили прежние версии кита, должны убираться при обновлении
mkdir -p "$PROJECT_DIR/.codex/commands" "$PROJECT_DIR/.codex/skills/legacy"
echo "# /legacy" > "$PROJECT_DIR/.codex/commands/legacy.md"

echo "▶ update-adapter-package.py"
UPDATE_LOG="$WORK_DIR/$ADAPTER-$PRESET-update.log"
if run_installer update-adapter-package.py "$UPDATE_LOG"; then
  pass "обновление завершилось успешно"
else
  cat "$UPDATE_LOG"
  fail "обновление завершилось с ошибкой"
fi
check "агенты кита на месте после обновления" test "$(count_files "$PROJECT_DIR/.aikit/agents" '*.md')" -gt 0
check "устаревшие .codex/commands и .codex/skills убраны" test ! -e "$PROJECT_DIR/.codex/commands" -a ! -e "$PROJECT_DIR/.codex/skills"
check_runtime_files " (после обновления)"

if [[ "$FAILURES" -gt 0 ]]; then
  echo "✗ $ADAPTER / $PRESET: проверок не пройдено — $FAILURES"
  exit 1
fi
echo "✓ $ADAPTER / $PRESET: все проверки пройдены"
