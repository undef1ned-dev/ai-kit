#!/usr/bin/env bash
# smoke-adapter.sh — Smoke-тест установки AIKit через адаптер (Codex, OpenCode)
#
# Использование (из любой папки):
#   bash scripts/ci/smoke-adapter.sh <adapter> <preset> [work-dir]
#
# Что делает:
#   1. Ставит пресет через install-adapter-package.py в пустой проект
#   2. Проверяет общие файлы кита и файлы конкретного runtime
#   3. Запускает update-adapter-package.py и проверяет, что установка не сломалась
#
# Глобальные папки пользователя (~/.codex/...) подменяются временными — тест не трогает HOME.

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
mkdir -p "$PROJECT_DIR"

export AIKIT_CODEX_PROMPTS_TARGET="$WORK_DIR/$ADAPTER-$PRESET-home/.codex/prompts"
export AIKIT_CODEX_SKILLS_TARGET="$WORK_DIR/$ADAPTER-$PRESET-home/.codex/skills"

FAILURES=0
pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; FAILURES=$((FAILURES + 1)); }
check() {
  local description="$1"; shift
  if "$@" >/dev/null 2>&1; then pass "$description"; else fail "$description"; fi
}

count_files() { find "$1" -type f -name "$2" 2>/dev/null | wc -l | tr -d ' '; }

# У каждого SKILL.md есть frontmatter с name и description — общий стандарт Claude Code, Codex и OpenCode
check_skills_frontmatter() {
  "$PYTHON_BIN" - "$1" <<'PY'
import pathlib, re, sys
skills = list(pathlib.Path(sys.argv[1]).glob("*/SKILL.md"))
assert skills, "нет скиллов"
for path in skills:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert match, f"нет frontmatter: {path}"
    for field in ("name", "description"):
        assert re.search(rf"(?m)^{field}:\s*\S", match.group(1)), f"нет {field}: {path}"
PY
}

# .codex/config.toml и агенты Codex — валидный TOML, у агентов есть обязательные поля
check_codex_toml() {
  "$PYTHON_BIN" - "$PROJECT_DIR/.codex" <<'PY'
import pathlib, sys, tomllib
root = pathlib.Path(sys.argv[1])
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

echo "▶ Адаптер $ADAPTER, пресет $PRESET → $PROJECT_DIR"

echo "▶ install-adapter-package.py"
"$PYTHON_BIN" "$KIT_ROOT/scripts/install-adapter-package.py" "$ADAPTER" --preset "$PRESET" --workspace "$PROJECT_DIR" > "$WORK_DIR/$ADAPTER-$PRESET-install.log" 2>&1 \
  || { cat "$WORK_DIR/$ADAPTER-$PRESET-install.log"; echo "✗ Установка завершилась с ошибкой"; exit 1; }

check "агенты кита установлены (.aikit/agents)" test "$(count_files "$PROJECT_DIR/.aikit/agents" '*.md')" -gt 0
check "скиллы кита установлены (.aikit/skills)" test "$(count_files "$PROJECT_DIR/.aikit/skills" '*.md')" -gt 0
check "память проекта создана" test -d "$PROJECT_DIR/.aikit/memory"
check "манифест пакета записан" test -s "$PROJECT_DIR/.aikit/package.manifest.json"
check "нет нераскрытых шаблонов {{...}}" bash -c "! grep -rlF '{{' '$PROJECT_DIR/.aikit/agents' '$PROJECT_DIR/.aikit/skills'"

case "$ADAPTER" in
  codex)
    check ".codex/config.toml и агенты — валидный TOML" check_codex_toml
    check "скиллы Codex с frontmatter name/description" check_skills_frontmatter "$PROJECT_DIR/.codex/skills"
    check "команды Codex установлены" test "$(count_files "$PROJECT_DIR/.codex/commands" '*.md')" -gt 0
    ;;
  opencode)
    check "инструкция OpenCode создана" test -s "$PROJECT_DIR/.opencode/AIKIT.md"
    ;;
esac

echo "▶ update-adapter-package.py"
if "$PYTHON_BIN" "$KIT_ROOT/scripts/update-adapter-package.py" "$ADAPTER" --preset "$PRESET" --workspace "$PROJECT_DIR" > "$WORK_DIR/$ADAPTER-$PRESET-update.log" 2>&1; then
  pass "обновление завершилось успешно"
else
  cat "$WORK_DIR/$ADAPTER-$PRESET-update.log"
  fail "обновление завершилось с ошибкой"
fi
check "агенты на месте после обновления" test "$(count_files "$PROJECT_DIR/.aikit/agents" '*.md')" -gt 0
[[ "$ADAPTER" == "codex" ]] && check ".codex/config.toml валиден после обновления" check_codex_toml

if [[ "$FAILURES" -gt 0 ]]; then
  echo "✗ $ADAPTER / $PRESET: проверок не пройдено — $FAILURES"
  exit 1
fi
echo "✓ $ADAPTER / $PRESET: все проверки пройдены"
