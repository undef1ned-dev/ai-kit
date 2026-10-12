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

# Скиллы: <name>/SKILL.md с name = папка и description, все из .config-version на месте
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
PY
}

# MCP: .mcp.json валиден, есть context7 из base, версии закреплены, свой сервер пользователя сохранён (если был)
check_mcp() {
  "$PYTHON_BIN" - "$PROJECT_DIR" "${1:-}" <<'PY'
import json, pathlib, sys
project, user_server = pathlib.Path(sys.argv[1]), sys.argv[2]
text = (project / ".mcp.json").read_text(encoding="utf-8")
servers = json.loads(text)["mcpServers"]
assert "context7" in servers, "нет context7"
assert "@latest" not in text, "версия не закреплена"
if user_server:
    assert user_server in servers, "сервер пользователя удалён"
settings = json.loads((project / ".claude" / "settings.json").read_text(encoding="utf-8"))
assert "mcpServers" not in settings, "MCP в settings.json"
gitignore = project / ".gitignore"
assert not gitignore.exists() or ".claude/settings.json" not in gitignore.read_text(encoding="utf-8"), "settings.json в .gitignore"
PY
}

# .aikit/profiles.json: контракты всех профилей пресета с агентами по ролям; правка команды проекта сохранена (если была)
check_profile_contracts() {
  "$PYTHON_BIN" - "$PROJECT_DIR" "$KIT_ROOT/presets/$PRESET.json" "${1:-}" <<'PY'
import json, pathlib, sys
project, preset, edited = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
expected = json.loads(preset.read_text(encoding="utf-8"))["profiles"]
contracts = json.loads((project / ".aikit" / "profiles.json").read_text(encoding="utf-8"))["profiles"]
assert list(contracts) == expected, f"профили {list(contracts)} вместо {expected}"
for name, contract in contracts.items():
    assert set(contract["agents"]) == {"architect", "coder", "tester", "reviewer"}, f"{name}: нет агентов по ролям"
    assert contract["commands"].get("lint"), f"{name}: нет команды lint"
if edited:
    first = contracts[expected[0]]["commands"]
    assert first.get("test") == "custom-test", "правка команды test затёрта"
    assert "run" not in first, "удалённая командой run вернулась"
PY
}

# Команда проекта правит контракт: своя команда test, без run
edit_profile_contract() {
  "$PYTHON_BIN" - "$PROJECT_DIR/.aikit/profiles.json" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
commands = next(iter(data["profiles"].values()))["commands"]
commands["test"] = "custom-test"
commands.pop("run", None)
path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
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
check "скиллы установлены: name = папка, есть description" check_skills
check "общий implement-feature: один на проект, без копий с префиксом профиля" bash -c "test -f .claude/skills/implement-feature/SKILL.md && ! ls -d .claude/skills/*-implement-feature 2>/dev/null"
check "нет устаревшей папки .claude/commands" test ! -e .claude/commands
check "скилл git-commit установлен" test -f .claude/skills/git-commit/SKILL.md
check "скилл git-branch установлен" test -f .claude/skills/git-branch/SKILL.md
check "нет нераскрытых шаблонов {{...}}" bash -c '! grep -rlF "{{" .claude CLAUDE.md'
check ".mcp.json: серверы с закреплёнными версиями, settings.json без MCP" check_mcp
check ".aikit/profiles.json: контракты профилей пресета" check_profile_contracts
check "память проекта создана" test -d .aikit/memory
check "версия конфигурации записана" test -s .claude/.config-version

# Прежние версии кита ставили команды в .claude/commands/, а смена набора скиллов оставляла старые папки
mkdir -p .claude/commands .claude/skills/legacy-kit-skill
echo "# legacy" > .claude/commands/security-check.md
echo "# своя команда" > .claude/commands/my-own.md
echo "# legacy" > .claude/skills/legacy-kit-skill/SKILL.md
# Свой MCP-сервер пользователя и правило .gitignore от прежних версий кита
"$PYTHON_BIN" -c 'import json; p = ".mcp.json"; d = json.load(open(p, encoding="utf-8")); d["mcpServers"]["my-server"] = {"command": "my-mcp"}; json.dump(d, open(p, "w", encoding="utf-8"))'
printf "node_modules/\n\n# Claude Code (локальные настройки MCP — у каждого свои пути)\n.claude/settings.json\n" > .gitignore
sed -i.bak 's/^skills=/skills=legacy-kit-skill /' .claude/.config-version && rm -f .claude/.config-version.bak
edit_profile_contract

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
check ".mcp.json после обновления: серверы кита и пользователя, .gitignore очищен" check_mcp my-server
check ".gitignore: свои правила сохранены" grep -qx "node_modules/" .gitignore
check ".aikit/profiles.json после обновления: правки команд проекта сохранены" check_profile_contracts edited

if [[ "$FAILURES" -gt 0 ]]; then
  echo "✗ Пресет $PRESET: проверок не пройдено — $FAILURES"
  echo "--- attach.log ---"; cat attach.log
  exit 1
fi
echo "✓ Пресет $PRESET: все проверки пройдены"
