#!/usr/bin/env bash
# smoke-attach.sh — Smoke-тест установки AIKit на пустой проект
#
# Использование (из любой папки):
#   bash scripts/ci/smoke-attach.sh <preset> [work-dir]
#
# Что делает:
#   1. Создаёт пустой git-проект (в work-dir или во временной папке)
#   2. Запускает attach.sh --preset <preset> и проверяет результат
#   3. Запускает update.sh --auto и проверяет, что установка не сломалась

set -eo pipefail

PRESET="${1:-}"
[[ -n "$PRESET" ]] || { echo "Использование: bash scripts/ci/smoke-attach.sh <preset> [work-dir]" >&2; exit 2; }

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PRESET_FILE="$KIT_ROOT/presets/$PRESET.json"
[[ -f "$PRESET_FILE" ]] || { echo "Пресет не найден: $PRESET_FILE" >&2; exit 2; }

PYTHON_BIN="$(command -v python3 || command -v python)"
WORK_DIR="${2:-$(mktemp -d)}"
PROJECT_DIR="$WORK_DIR/project-$PRESET"
mkdir -p "$PROJECT_DIR"

FAILURES=0
pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; FAILURES=$((FAILURES + 1)); }
check() {
  local description="$1"; shift
  if "$@" >/dev/null 2>&1; then pass "$description"; else fail "$description"; fi
}

# Проверки settings.json: валидный JSON, без соавторства, запрет на чтение .env
check_settings() {
  "$PYTHON_BIN" - "$PROJECT_DIR/.claude/settings.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    settings = json.load(f)
attribution = settings.get("attribution", {})
assert attribution.get("commit") == "" and attribution.get("pr") == "", "attribution не пустой"
deny = settings.get("permissions", {}).get("deny", [])
assert any(".env" in rule for rule in deny), "нет deny на .env"
PY
}

check_agents_frontmatter() {
  local f
  for f in "$PROJECT_DIR"/.claude/agents/*.md; do
    head -1 "$f" | grep -q '^---' || { echo "нет frontmatter: $f" >&2; return 1; }
    grep -q '^name:' "$f" || { echo "нет name: $f" >&2; return 1; }
  done
}

check_profiles_in_claude_md() {
  local profile heading
  for profile in $("$PYTHON_BIN" -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1], encoding="utf-8"))["profiles"]))' "$PRESET_FILE" | tr -d '\r'); do
    heading="$(head -1 "$KIT_ROOT/profiles/$profile/CLAUDE.md")"
    grep -qF "$heading" "$PROJECT_DIR/CLAUDE.md" || { echo "в CLAUDE.md нет профиля $profile" >&2; return 1; }
  done
}

# Скиллы: <name>/SKILL.md с name = папка и description, шаблоны раскрыты, все из .config-version на месте
check_skills() {
  "$PYTHON_BIN" - "$PROJECT_DIR/.claude" <<'PY'
import json, pathlib, re, sys
claude = pathlib.Path(sys.argv[1])
config = dict(line.split("=", 1) for line in (claude / ".config-version").read_text(encoding="utf-8").splitlines() if "=" in line)
expected = config.get("skills", "").split()
assert expected, "в .config-version нет skills="
for name in expected:
    path = claude / "skills" / name / "SKILL.md"
    assert path.exists(), f"нет скилла {name}"
    match = re.match(r"---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    assert match, f"нет frontmatter: {name}"
    fields = dict(re.findall(r"(?m)^([\w-]+):\s*(.*)$", match.group(1)))
    assert fields.get("name", "").strip('"') == name, f"name не совпадает с папкой: {name}"
    assert fields.get("description", "").strip(), f"нет description: {name}"
    assert "template" not in fields, f"шаблон не раскрыт: {name}"
PY
}

count_files() { find "$1" -type f -name "$2" 2>/dev/null | wc -l | tr -d ' '; }

echo "▶ Пресет $PRESET → $PROJECT_DIR"
cd "$PROJECT_DIR"
git init -q

echo "▶ attach.sh"
bash "$KIT_ROOT/scripts/attach.sh" --preset "$PRESET" > attach.log 2>&1 || { cat attach.log; echo "✗ attach.sh завершился с ошибкой"; exit 1; }

check "CLAUDE.md создан" test -s CLAUDE.md
check "CLAUDE.md содержит базовые правила" grep -qF "$(head -1 "$KIT_ROOT/base/CLAUDE.md")" CLAUDE.md
check "CLAUDE.md содержит все профили пресета" check_profiles_in_claude_md
check "PRODUCT.md создан" test -s PRODUCT.md
check ".claude/settings.json корректен" check_settings
check "агенты установлены" test "$(count_files .claude/agents '*.md')" -gt 0
check "у всех агентов есть frontmatter с name" check_agents_frontmatter
check "скиллы установлены: name = папка, есть description, шаблоны раскрыты" check_skills
check "нет устаревшей папки .claude/commands" test ! -e .claude/commands
check "скилл git-commit установлен" test -f .claude/skills/git-commit/SKILL.md
check "скилл git-branch установлен" test -f .claude/skills/git-branch/SKILL.md
check "нет нераскрытых шаблонов {{...}}" bash -c '! grep -rlF "{{" .claude CLAUDE.md'
check "память проекта создана" test -d .aikit/memory
check "версия конфигурации записана" test -s .claude/.config-version

# Прежние версии кита ставили команды в .claude/commands/, а смена набора скиллов оставляла старые папки
mkdir -p .claude/commands .claude/skills/legacy-kit-skill
echo "# legacy" > .claude/commands/security-check.md
echo "# своя команда" > .claude/commands/my-own.md
echo "# legacy" > .claude/skills/legacy-kit-skill/SKILL.md
sed -i.bak 's/^skills=/skills=legacy-kit-skill /' .claude/.config-version && rm -f .claude/.config-version.bak

echo "▶ update.sh --auto"
if bash "$KIT_ROOT/scripts/update.sh" --auto > update.log 2>&1; then
  pass "update.sh завершился успешно"
else
  cat update.log
  fail "update.sh завершился с ошибкой"
fi
check ".claude/settings.json корректен после обновления" check_settings
check "агенты на месте после обновления" test "$(count_files .claude/agents '*.md')" -gt 0
check "скиллы корректны после обновления" check_skills
check "старые скиллы и команды кита убраны" test ! -e .claude/skills/legacy-kit-skill -a ! -e .claude/commands/security-check.md
check "своя команда пользователя сохранена" test -f .claude/commands/my-own.md

if [[ "$FAILURES" -gt 0 ]]; then
  echo "✗ Пресет $PRESET: проверок не пройдено — $FAILURES"
  echo "--- attach.log ---"; cat attach.log
  exit 1
fi
echo "✓ Пресет $PRESET: все проверки пройдены"
