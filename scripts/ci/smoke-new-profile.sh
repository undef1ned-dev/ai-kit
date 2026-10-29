#!/usr/bin/env bash
# smoke-new-profile.sh — Smoke-тест «новый стек без правок ядра»
#
# Использование (из любой папки):
#   bash scripts/ci/smoke-new-profile.sh [work-dir]
#
# Что делает:
#   1. Копирует кит во временную папку и создаёт в копии профиль java-spring через scripts/new-profile.py
#   2. Добавляет профилю пайплайн со своим агентом и прогоняет статические проверки копии — без правок ядра
#   3. Ставит vue-nuxt+java-spring в монорепо (web/ и api/) через attach.sh и адаптер Codex и проверяет результат

set -eo pipefail
# Сообщения скриптов кита с кириллицей печатаются и в консоли Windows
export PYTHONIOENCODING=utf-8

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="$(command -v python3 || command -v python)"
WORK_DIR="${1:-$(mktemp -d)}"
KIT_COPY="$WORK_DIR/kit"
PROFILES="vue-nuxt+java-spring"

FAILURES=0
pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; FAILURES=$((FAILURES + 1)); }
check() {
  local description="$1"; shift
  local log="$WORK_DIR/check.log"
  if "$@" > "$log" 2>&1; then
    pass "$description"
  else
    fail "$description"
    cat "$log"
  fi
}

# .aikit/profiles.json: оба профиля, агенты java-spring по ролям и quality-специалист, папки найдены по маркерам
check_contracts() {
  "$PYTHON_BIN" - "$1/.aikit/profiles.json" <<'PY'
import json, pathlib, sys
contracts = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["profiles"]
assert list(contracts) == ["vue-nuxt", "java-spring"], list(contracts)
spring = contracts["java-spring"]
assert spring["agents"] == {role: f"spring-{role}" for role in ("architect", "coder", "tester", "reviewer")}, spring["agents"]
assert spring["root"] == "api" and contracts["vue-nuxt"]["root"] == "web", (spring["root"], contracts["vue-nuxt"]["root"])
assert spring["commands"]["test"] == "./mvnw test", spring["commands"]
assert spring["specialists"]["quality"]["agent"] == "spring-quality-analyst", spring["specialists"]
assert spring["pipelines"]["api-docs"]["steps"] == ["spring-api-documenter", "spring-reviewer"], spring["pipelines"]
PY
}

# Пайплайн профиля: свой агент и запись в pipelines контракта (agent — имя агента, если его нет, проверка должна упасть)
add_pipeline() {
  "$PYTHON_BIN" - "$KIT_COPY/profiles/java-spring" "$1" <<'PY'
import json, pathlib, sys
profile, agent = pathlib.Path(sys.argv[1]), sys.argv[2]
documenter = profile / "agents" / "spring-api-documenter.md"
documenter.write_text(
    '---\nname: spring-api-documenter\ndescription: Описывает API в OpenAPI.\noutput_block: "API_DOCS"\n---\n\nОпиши API.\n',
    encoding="utf-8",
)
native = profile / "codex/agents/spring-api-documenter.toml"
native.write_bytes(b'name = "spring-api-documenter"\ndescription = "API documentation"\nmodel = "gpt-6.1-sol"\nmodel_reasoning_effort = "medium"\ndeveloper_instructions = "Return API_DOCS with API documentation."\n')
catalog = profile / "codex/catalog.json"
metadata = json.loads(catalog.read_text(encoding="utf-8"))
metadata["agents"]["spring-api-documenter"] = {"output_block": "API_DOCS"}
catalog.write_bytes((json.dumps(metadata) + "\n").encode("utf-8"))
manifest = profile / "profile.manifest.json"
data = json.loads(manifest.read_text(encoding="utf-8"))
data["pipelines"] = {"api-docs": {"when": "нужна только документация API без изменения кода", "steps": [agent, "spring-reviewer"]}}
manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
  # The catalog page of the docs site shows the new profile — rebuild it, as the author of a profile does
  (cd "$KIT_COPY" && "$PYTHON_BIN" scripts/generate-docs.py >/dev/null && git add -A)
}

echo "▶ Копия кита → $KIT_COPY"
mkdir -p "$KIT_COPY"
(cd "$KIT_ROOT" && git ls-files -co --exclude-standard -z | tr -d '\r' | while IFS= read -r -d '' file; do
  [[ -f "$file" ]] || continue
  mkdir -p "$KIT_COPY/$(dirname "$file")" && cp "$file" "$KIT_COPY/$file"
done)
(cd "$KIT_COPY" && git init -q && git add -A)

echo "▶ new-profile.py java-spring"
"$PYTHON_BIN" "$KIT_COPY/scripts/new-profile.py" java-spring --role backend --stack "Java 21, Spring Boot 3, JUnit 5" \
  --test "./mvnw test" --lint "./mvnw checkstyle:check" --build "./mvnw package" \
  --root-marker pom.xml --path-signal src/main/java/ --path-signal src/test/java/
check "повторное создание того же профиля отклонено" bash -c "! '$PYTHON_BIN' '$KIT_COPY/scripts/new-profile.py' java-spring --role backend --stack x --test x --root-marker x --path-signal x"
(cd "$KIT_COPY" && git add -A)
add_pipeline spring-missing-agent
check "пайплайн с несуществующим агентом отклонён статической проверкой" bash -c "! (cd '$KIT_COPY' && bash scripts/ci/static-checks.sh)"
add_pipeline spring-api-documenter
check "копия кита с новым профилем и пайплайном проходит статические проверки" bash -c "cd '$KIT_COPY' && bash scripts/ci/static-checks.sh"

make_monorepo() {
  mkdir -p "$1/web" "$1/api"
  touch "$1/web/nuxt.config.ts" "$1/api/pom.xml"
}

echo "▶ attach.sh $PROFILES"
PROJECT_DIR="$WORK_DIR/attach-project"
make_monorepo "$PROJECT_DIR"
(cd "$PROJECT_DIR" && git init -q && bash "$KIT_COPY/scripts/attach.sh" "$PROFILES" > "$WORK_DIR/attach.log" 2>&1) \
  || { cat "$WORK_DIR/attach.log"; echo "✗ attach.sh завершился с ошибкой"; exit 1; }
check "агенты java-spring установлены" test -f "$PROJECT_DIR/.claude/agents/spring-architect.md" -a -f "$PROJECT_DIR/.claude/agents/spring-reviewer.md"
check ".aikit/profiles.json: java-spring в api/, vue-nuxt в web/" check_contracts "$PROJECT_DIR"
check "settings.json разрешает команды профиля" grep -qF 'Bash(./mvnw *)' "$PROJECT_DIR/.claude/settings.json"
check "CLAUDE.md содержит правила java-spring" grep -q "Java Spring Profile" "$PROJECT_DIR/CLAUDE.md"

echo "▶ install-adapter-package.py codex $PROFILES"
CODEX_DIR="$WORK_DIR/codex-project"
FAKE_HOME="$WORK_DIR/home"
make_monorepo "$CODEX_DIR"
mkdir -p "$FAKE_HOME"
HOME="$FAKE_HOME" USERPROFILE="$FAKE_HOME" "$PYTHON_BIN" "$KIT_COPY/scripts/install-adapter-package.py" codex \
  --profile "$PROFILES" --workspace "$CODEX_DIR" > "$WORK_DIR/codex.log" 2>&1 \
  || { cat "$WORK_DIR/codex.log"; echo "✗ Установка Codex завершилась с ошибкой"; exit 1; }
check "агенты java-spring для Codex установлены" test -f "$CODEX_DIR/.codex/agents/spring-architect.toml"
check ".aikit/profiles.json (Codex): java-spring в api/, vue-nuxt в web/" check_contracts "$CODEX_DIR"

if [[ "$FAILURES" -gt 0 ]]; then
  echo "✗ Новый профиль: ошибок — $FAILURES"
  exit 1
fi
echo "✓ Новый профиль собирается и ставится без правок ядра"
