#!/usr/bin/env bash
# static-checks.sh — Статические проверки репозитория AIKit
#
# Использование (из корня репозитория):
#   bash scripts/ci/static-checks.sh
#
# Что проверяет (только файлы под git):
#   1. Синтаксис всех *.sh (bash -n) и грубые ошибки через shellcheck, если он установлен
#   2. Синтаксис всех *.py (компиляция без записи __pycache__)
#   3. Корректность всех *.json
#   4. Каталог документации видит все скиллы-папки профилей и паков
#   5. Контракт профиля (profile.manifest.json) полон и ссылается на существующих агентов (роли, специалисты, пайплайны), у каждого профиля есть специалист quality,
#      ревьюер профиля отвечает в формате REVIEW_RESULT, который читает /implement-feature
#   6. Базовые оркестраторы и скиллы не называют агентов профилей по имени — берут их из .aikit/profiles.json
#   7. Имена агентов и скиллов уникальны во всём ките — любые профили и паки ставятся вместе без переименований
#   8. Сайт документации docs/site/ собран из актуальных исходников, ссылки и якоря не битые, все скиллы есть в docs/guide/commands.md
#   9. Сценарии хуков base/hooks/aikit_hook.py: что блокируется и что пропускается, линтер, тесты, контекст сессии
#  10. Манифесты плагинов и маркетплейса собраны из актуальных исходников и указывают на существующие файлы
#  11. Модели агентов: у каждого агента уровень из adapters/models.json, модели всех runtime, переопределения проекта (.aikit/models.json)
#  12. Эвалы evals/ разбираются, а раннер scripts/run-evals.py оценивает их без вызовов модели (подставной codex)
#  13. Мод AIKit Deck: hooks/hooks.json указывает на существующий модуль, группы панели — на существующие скиллы, синтаксис JS.
#      Тесты мода (claude plugin test) запускает run-all.sh, если установлен Claude Code

set -eo pipefail

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$KIT_ROOT"
PYTHON_BIN="$(command -v python3 || command -v python)"
# Сообщения с ✗ и кириллицей печатаются и в консоли Windows
export PYTHONIOENCODING=utf-8
FAILURES=0

list_files() { git ls-files -z -- "$1" | tr '\0' '\n' | tr -d '\r'; }

echo "▶ bash -n"
while IFS= read -r f; do
  [[ -n "$f" ]] || continue
  bash -n "$f" || { echo "  ✗ $f"; FAILURES=$((FAILURES + 1)); }
done < <(list_files '*.sh')

if command -v shellcheck >/dev/null 2>&1; then
  echo "▶ shellcheck (только ошибки)"
  list_files '*.sh' | tr '\n' '\0' | xargs -0 shellcheck --severity=error || FAILURES=$((FAILURES + 1))
else
  echo "! shellcheck не установлен — пропускаю"
fi

echo "▶ Python: синтаксис"
list_files '*.py' | "$PYTHON_BIN" -c '
import sys
failed = 0
for path in filter(None, (line.strip() for line in sys.stdin)):
    try:
        with open(path, encoding="utf-8") as f:
            compile(f.read(), path, "exec")
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"  ✗ {path}: {e}")
        failed += 1
sys.exit(1 if failed else 0)
' || FAILURES=$((FAILURES + 1))

echo "▶ JSON: синтаксис"
list_files '*.json' | "$PYTHON_BIN" -c '
import json, sys
failed = 0
for path in filter(None, (line.strip() for line in sys.stdin)):
    try:
        with open(path, encoding="utf-8") as f:
            json.load(f)
    except (ValueError, UnicodeDecodeError) as e:
        print(f"  ✗ {path}: {e}")
        failed += 1
sys.exit(1 if failed else 0)
' || FAILURES=$((FAILURES + 1))

echo "▶ Каталог: все скиллы профилей и паков найдены, у всех есть description"
"$PYTHON_BIN" -c '
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location("catalog", "scripts/generate-docs.py")
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)
sections = catalog.collect_data(pathlib.Path("."))
found = {(key, skill["name"]) for key, section in sections.items() for skill in section["skills"]}
expected = {(path.parts[1], path.parent.name) for path in pathlib.Path("profiles").glob("*/skills/*/SKILL.md") if path.parts[1] in sections}
expected |= {("pack-" + path.parts[1], path.parent.name) for path in pathlib.Path("packs").glob("*/skills/*/SKILL.md")}
missing = sorted(expected - found)
empty = sorted(skill["name"] for section in sections.values() for skill in section["skills"] if not skill.get("description"))
for item in missing:
    print(f"  ✗ скилл не попал в каталог: {item}")
for name in empty:
    print(f"  ✗ нет description: {name}")
sys.exit(1 if missing or empty else 0)
' || FAILURES=$((FAILURES + 1))

echo "▶ Контракт профиля: обязательные поля, агенты по ролям существуют, известные команды"
"$PYTHON_BIN" -c '
import json, pathlib, sys
ROLES = {"architect", "coder", "tester", "reviewer"}
COMMANDS = {"install", "lint", "format", "test", "build", "run"}
REQUIRED = {"profile", "label", "role", "stack", "agents", "commands", "root_markers", "path_signals"}
REVIEW_VERDICT = "VERDICT: APPROVE | APPROVE_WITH_COMMENTS | REQUEST_CHANGES"
errors = []
for manifest in sorted(pathlib.Path("profiles").glob("*/profile.manifest.json")):
    profile = manifest.parent
    data = json.loads(manifest.read_text(encoding="utf-8"))
    def agent_exists(name):
        return (profile / "agents" / f"{name}.md").is_file()
    missing = REQUIRED - data.keys()
    if missing:
        errors.append(f"{manifest}: нет полей {sorted(missing)}")
        continue
    if data["profile"] != profile.name:
        errors.append(f"{manifest}: profile не совпадает с папкой")
    if set(data["agents"]) != ROLES:
        errors.append(f"{manifest}: agents должны быть ровно по ролям {sorted(ROLES)}")
    errors += [f"{manifest}: нет агента {name}" for name in data["agents"].values() if not agent_exists(name)]
    reviewer = profile / "agents" / (data["agents"].get("reviewer", "") + ".md")
    if reviewer.is_file() and REVIEW_VERDICT not in reviewer.read_text(encoding="utf-8"):
        errors.append(f"{reviewer}: формат REVIEW_RESULT не тот, что читает /implement-feature ({REVIEW_VERDICT})")
    if "quality" not in data.get("specialists", {}):
        errors.append(f"{manifest}: нет специалиста quality (его зовут /coverage-check и /tech-debt)")
    for name, spec in data.get("specialists", {}).items():
        if not agent_exists(spec.get("agent", "")) or not spec.get("when", "").strip():
            errors.append(f"{manifest}: специалист {name} без агента или без when")
    for name, pipeline in data.get("pipelines", {}).items():
        steps = pipeline.get("steps", [])
        if not pipeline.get("when", "").strip() or not steps:
            errors.append(f"{manifest}: пайплайн {name} без when или без steps")
        errors += [f"{manifest}: пайплайн {name}: нет агента {step}" for step in steps if not agent_exists(step)]
    unknown = set(data["commands"]) - COMMANDS
    if unknown or "test" not in data["commands"]:
        errors.append(f"{manifest}: команды {sorted(unknown)} неизвестны или нет test")
    if not data["path_signals"]:
        errors.append(f"{manifest}: пустые path_signals")
    if not data["root_markers"]:
        errors.append(f"{manifest}: пустые root_markers")
    extensions = data.get("code_extensions", [])
    if not isinstance(extensions, list) or any(not str(item).startswith(".") for item in extensions):
        errors.append(f"{manifest}: code_extensions — список расширений с точкой: [\".py\"]")
for error in errors:
    print(f"  ✗ {error}")
sys.exit(1 if errors else 0)
' || FAILURES=$((FAILURES + 1))

echo "▶ Базовые оркестраторы: агенты профилей только из контракта, без имён в тексте"
"$PYTHON_BIN" -c '
import json, pathlib, re, sys
names = set()
for manifest in pathlib.Path("profiles").glob("*/profile.manifest.json"):
    data = json.loads(manifest.read_text(encoding="utf-8"))
    names |= set(data["agents"].values()) | {spec["agent"] for spec in data.get("specialists", {}).values()}
files = [*pathlib.Path("base/skills").glob("*/SKILL.md"), pathlib.Path("base/agents/workflow-runner.md"), pathlib.Path("base/agents/tech-planner.md")]
errors = []
for path in files:
    text = path.read_text(encoding="utf-8")
    errors += [f"{path}: {name}" for name in sorted(names) if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text)]
for error in errors:
    print(f"  ✗ имя агента профиля вместо роли из контракта: {error}")
sys.exit(1 if errors else 0)
' || FAILURES=$((FAILURES + 1))

echo "▶ Имена агентов и скиллов уникальны во всём ките, name агента совпадает с файлом"
"$PYTHON_BIN" -c '
import collections, pathlib, re, sys
layers = [pathlib.Path("base"), *pathlib.Path("profiles").iterdir(), *pathlib.Path("packs").iterdir()]
agents, skills, errors = collections.defaultdict(list), collections.defaultdict(list), []
for layer in layers:
    for path in layer.glob("agents/*.md"):
        agents[path.stem].append(str(layer))
        match = re.search(r"(?m)^name:\s*\"?([\w-]+)", path.read_text(encoding="utf-8"))
        if not match or match.group(1) != path.stem:
            errors.append(f"{path}: name не совпадает с именем файла")
    for path in [*layer.glob("skills/*/SKILL.md"), *layer.glob("plugin-skills/*/SKILL.md")]:
        skills[path.parent.name].append(str(layer))
errors += [f"агент {name} есть в {owners}" for name, owners in agents.items() if len(owners) > 1]
errors += [f"скилл {name} есть в {owners}" for name, owners in skills.items() if len(owners) > 1]
for error in errors:
    print(f"  ✗ {error}")
sys.exit(1 if errors else 0)
' || FAILURES=$((FAILURES + 1))

echo "▶ Документация: docs/site/ собран из docs/guide/ и исходников кита"
"$PYTHON_BIN" scripts/generate-docs.py --check || FAILURES=$((FAILURES + 1))

echo "▶ Плагины: манифесты Claude Code и Codex собраны из исходников кита"
"$PYTHON_BIN" scripts/build-plugins.py --check && echo "  ✓ маркетплейс и плагины актуальны" || FAILURES=$((FAILURES + 1))

echo "▶ Хуки: сценарии base/hooks/aikit_hook.py"
"$PYTHON_BIN" scripts/ci/test-hooks.py || FAILURES=$((FAILURES + 1))
if command -v node &>/dev/null; then
  # The plugin is an ES module: node checks it as .mjs
  PLUGIN_COPY="$(mktemp -d)/aikit-hooks.mjs"
  cp base/hooks/opencode-plugin.js "$PLUGIN_COPY"
  node --check "$PLUGIN_COPY" && echo "  ✓ плагин OpenCode: синтаксис JS" || { echo "  ✗ плагин OpenCode: синтаксис JS"; FAILURES=$((FAILURES + 1)); }
fi

echo "▶ Модели агентов: уровни, adapters/models.json, переопределения проекта"
"$PYTHON_BIN" scripts/ci/test-agent-models.py || FAILURES=$((FAILURES + 1))

echo "▶ Эвалы: кейсы evals/ и раннер scripts/run-evals.py (без вызовов модели)"
"$PYTHON_BIN" scripts/ci/test-run-evals.py || FAILURES=$((FAILURES + 1))

echo "▶ AIKit Deck: мод панели (hooks/hooks.json, deck/)"
"$PYTHON_BIN" -c '
import json, pathlib, re, sys
errors = []
hooks = pathlib.Path("hooks/hooks.json")
modules = json.loads(hooks.read_text(encoding="utf-8")).get("modules", [])
if len(modules) != 1:
    errors.append("hooks/hooks.json: в modules должен быть один путь")
for module in modules:
    if not (hooks.parent / module).resolve().is_file():
        errors.append(f"hooks/hooks.json: нет модуля {module}")
catalog = pathlib.Path("deck/catalog.js").read_text(encoding="utf-8")
skills = {path.parent.name for folder in ("base/skills", "base/plugin-skills") for path in pathlib.Path(folder).glob("*/SKILL.md")}
for block in re.findall(r"skills: \[([^\]]*)\]", catalog):
    for name in re.findall(r"\x27([\w-]+)\x27", block):
        if name not in skills:
            errors.append(f"deck/catalog.js: в группе панели скилл {name}, которого нет в base/")
for error in errors:
    print(f"  ✗ {error}")
if not errors:
    print("  ✓ модуль на месте, группы панели ссылаются на существующие скиллы")
sys.exit(1 if errors else 0)
' || FAILURES=$((FAILURES + 1))
if command -v node &>/dev/null; then
  # The modules are ES modules: node checks them as .mjs
  DECK_COPY="$(mktemp -d)"
  for module in deck/*.js; do
    copy="$DECK_COPY/$(basename "$module" .js).mjs"
    cp "$module" "$copy"
    node --check "$copy" && echo "  ✓ $module: синтаксис JS" || { echo "  ✗ $module: синтаксис JS"; FAILURES=$((FAILURES + 1)); }
  done
fi

if [[ "$FAILURES" -gt 0 ]]; then
  echo "✗ Статические проверки: ошибок — $FAILURES"
  exit 1
fi
echo "✓ Статические проверки пройдены"
