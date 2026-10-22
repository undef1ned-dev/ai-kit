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
#   6. Агенты и скиллы base/ не называют агентов профилей и паков по имени — берут их из .aikit/profiles.json
#   7. Имена агентов и скиллов уникальны во всём ките — любые профили и паки ставятся вместе без переименований
#   8. Сайт документации docs/site/ собран из актуальных исходников, ссылки и якоря не битые, все скиллы есть в docs/guide/commands.md
#   9. Сценарии хуков base/hooks/aikit_hook.py: что блокируется и что пропускается, линтер, тесты, контекст сессии
#  10. Манифесты плагинов и маркетплейса собраны из актуальных исходников и указывают на существующие файлы, version в них равна VERSION;
#      bump версии по Conventional Commits (scripts/ci/test-bump-version.py)
#  11. Модели агентов: у каждого агента уровень из adapters/models.json, модели всех runtime, переопределения проекта (.aikit/models.json)
#  12. Эвалы evals/ разбираются, а раннер scripts/run-evals.py оценивает их без вызовов модели (подставной codex)
#  13. Мод AIKit Deck: hooks/hooks.json указывает на существующий модуль, группы панели — на существующие скиллы, синтаксис JS.
#      Тесты мода (claude plugin test) запускает run-all.sh, если установлен Claude Code
#  14. MCP в агентах: если в тексте агента есть mcp__<сервер>__, то в его tools этот сервер разрешён (иначе субагент не получит MCP)
#  15. Пути кита в обратных кавычках (`docs/...`, `scripts/...`, `base/...` и т.п.) в агентах, скиллах и шаблоне профиля существуют
#  16. depends_on и orchestrates агентов указывают на существующих агентов
#  17. Агенты и скиллы профилей и шаблон профиля не зовут менеджер пакетов (npm, npx, pnpm, yarn) — команды из .aikit/profiles.json
#  18. Агент или скилл с командой git commit следует режиму коммитов скилла git-commit
#  19. Скиллы разработки кита: у копий .claude/skills/<имя> и .agents/skills/<имя> одинаковые name и description

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
import json, pathlib, re, sys
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
    # Deck buttons: run by argv without a shell, so no shell syntax and no {files}
    for name, action in data.get("actions", {}).items():
        argv = action.get("argv") if isinstance(action, dict) else None
        if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item.strip() for item in argv):
            errors.append(f"{manifest}: действие {name}: argv — непустой список строк")
        elif any(re.search(r"[&|<>^%\"{}]", item) for item in argv):
            errors.append(f"{manifest}: действие {name}: в argv синтаксис shell или подстановка — действия запускаются без shell")
        if not isinstance(action, dict) or not str(action.get("label", "")).strip():
            errors.append(f"{manifest}: действие {name} без label")
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

echo "▶ Ядро base/: агенты профилей и паков только из контракта, без имён в тексте"
"$PYTHON_BIN" -c '
import pathlib, re, sys
# Base works with any set of profiles and packs, so it names roles from the contract, not their agents
names = {path.stem for layer in ("profiles", "packs") for path in pathlib.Path(layer).glob("*/agents/*.md")}
files = [*pathlib.Path("base/skills").glob("*/SKILL.md"), *pathlib.Path("base/plugin-skills").glob("*/SKILL.md"), *pathlib.Path("base/agents").glob("*.md")]
errors = []
for path in sorted(files):
    text = path.read_text(encoding="utf-8")
    errors += [f"{path.as_posix()}: {name}" for name in sorted(names) if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text)]
for error in errors:
    print(f"  ✗ имя агента профиля или пака вместо роли из контракта: {error}")
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

echo "▶ Скиллы только по явному вызову: рядом с disable-model-invocation — agents/openai.yaml для Codex"
"$PYTHON_BIN" -c '
import pathlib, re, sys
# Codex reads the same skill folder from the plugin and from the adapter install, so the policy lives in the source
patterns = ("base/skills/*/SKILL.md", "base/plugin-skills/*/SKILL.md", "profiles/*/skills/*/SKILL.md", "packs/*/skills/*/SKILL.md")
errors = []
for path in sorted(p for pattern in patterns for p in pathlib.Path(".").glob(pattern)):
    head = path.read_text(encoding="utf-8").partition("\n---\n")[0]
    explicit = bool(re.search(r"(?m)^disable-model-invocation:\s*true\s*$", head))
    policy = path.parent / "agents" / "openai.yaml"
    has_policy = policy.is_file() and bool(re.search(r"(?m)^\s*allow_implicit_invocation:\s*false\s*$", policy.read_text(encoding="utf-8")))
    if explicit and not has_policy:
        errors.append(f"{path.parent.as_posix()}: disable-model-invocation: true, но нет agents/openai.yaml с allow_implicit_invocation: false")
    if has_policy and not explicit:
        errors.append(f"{path.parent.as_posix()}: agents/openai.yaml запрещает автовызов в Codex, а в SKILL.md нет disable-model-invocation: true")
for error in errors:
    print(f"  ✗ {error}")
if not errors:
    print("  ✓ политика явного вызова одинакова в Claude Code и Codex")
sys.exit(1 if errors else 0)
' || FAILURES=$((FAILURES + 1))

echo "▶ CLAUDE.md в корне — копия base/CLAUDE.md"
"$PYTHON_BIN" -c '
import pathlib, sys
expected = pathlib.Path("base/CLAUDE.md").read_text(encoding="utf-8")
if pathlib.Path("CLAUDE.md").read_text(encoding="utf-8") != expected:
    print("  ✗ CLAUDE.md отстал от источников: скопируй в него base/CLAUDE.md (раздел «Карта репозитория» в docs/guide/developing-aikit.md)")
    sys.exit(1)
' || FAILURES=$((FAILURES + 1))

echo "▶ Документация: docs/site/ собран из docs/guide/ и исходников кита"
"$PYTHON_BIN" scripts/generate-docs.py --check || FAILURES=$((FAILURES + 1))

echo "▶ Плагины: манифесты Claude Code и Codex собраны из исходников кита"
"$PYTHON_BIN" scripts/build-plugins.py --check && echo "  ✓ маркетплейс и плагины актуальны, версия в манифестах равна VERSION" || FAILURES=$((FAILURES + 1))

echo "▶ Версия: bump по Conventional Commits (scripts/bump-version.py)"
"$PYTHON_BIN" scripts/ci/test-bump-version.py || FAILURES=$((FAILURES + 1))

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
# .claude/skills/ — own skills of the kit repository (improve-aikit), shown when the deck runs here
skills = {path.parent.name for folder in ("base/skills", "base/plugin-skills", ".claude/skills") for path in pathlib.Path(folder).glob("*/SKILL.md")}
for block in re.findall(r"skills: \[([^\]]*)\]", catalog):
    for name in re.findall(r"\x27([\w-]+)\x27", block):
        if name not in skills:
            errors.append(f"deck/catalog.js: в группе панели скилл {name}, которого нет в base/ и .claude/skills/")
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

echo "▶ MCP в агентах: инструмент из текста разрешён в tools"
"$PYTHON_BIN" -c '
import pathlib, re, sys
# An agent with an explicit tools list gets no MCP tools unless they are listed (in plugins the name is mcp__plugin_<plugin>_<server>__*)
errors = []
for path in sorted(pathlib.Path(".").glob("base/agents/*.md")) + sorted(pathlib.Path(".").glob("profiles/*/agents/*.md")) + sorted(pathlib.Path(".").glob("packs/*/agents/*.md")):
    text = path.read_text(encoding="utf-8")
    head, _, body = text.partition("\n---\n")
    tools_line = next((line for line in head.splitlines() if line.startswith("tools:")), None)
    if tools_line is None:
        continue
    allowed = [item.strip() for item in tools_line[len("tools:"):].split(",")]
    for server in sorted(set(re.findall(r"mcp__([A-Za-z0-9-]+)__", body))):
        listed = any(item.startswith(f"mcp__{server}__") or re.match(rf"mcp__plugin_.+_{re.escape(server)}__", item) for item in allowed)
        if not listed:
            errors.append(f"{path.as_posix()}: в тексте mcp__{server}__*, а в tools его нет — субагент не получит MCP")
for error in errors:
    print(f"  ✗ {error}")
if not errors:
    print("  ✓ MCP-инструменты из текста агентов перечислены в tools")
sys.exit(1 if errors else 0)
' || FAILURES=$((FAILURES + 1))

echo "▶ Пути кита в агентах и скиллах существуют"
"$PYTHON_BIN" -c '
import pathlib, re, sys
root = pathlib.Path(".")
files = [*root.glob("base/agents/*.md"), *root.glob("base/skills/*/SKILL.md"), *root.glob("base/plugin-skills/*/SKILL.md")]
files += [*root.glob("profiles/*/agents/*.md"), *root.glob("profiles/*/skills/*/SKILL.md")]
files += [*root.glob("packs/*/agents/*.md"), *root.glob("packs/*/skills/*/SKILL.md"), *root.glob("templates/profile/**/*.md")]
KIT_PATH = re.compile(r"`((?:docs|scripts|base|profiles|packs|templates|adapters|deck)/[^`\s]*)`")
PLACEHOLDER = re.compile(r"[<>{}*]|\.\.\.|…")
# Paths in the user project, not in the kit: the folder is created there
PROJECT_PATHS = {
    "docs/mvp",  # /analyze-mvp writes MVP documents into the project
}
errors = []
for path in sorted(files):
    for match in KIT_PATH.finditer(path.read_text(encoding="utf-8")):
        target = match.group(1)
        if PLACEHOLDER.search(target):
            continue
        target = re.split(r"[#:]", target)[0].rstrip("/.,")
        if target not in PROJECT_PATHS and not (root / target).exists():
            errors.append(f"{path.as_posix()}: нет пути {target} в ките (если это путь проекта пользователя — добавь его в PROJECT_PATHS)")
for error in errors:
    print(f"  ✗ {error}")
if not errors:
    print("  ✓ пути кита в агентах и скиллах существуют")
sys.exit(1 if errors else 0)
' || FAILURES=$((FAILURES + 1))

echo "▶ depends_on и orchestrates агентов указывают на существующих агентов"
"$PYTHON_BIN" -c '
import json, pathlib, re, sys
LAYERS = ("base/agents/*.md", "profiles/*/agents/*.md", "packs/*/agents/*.md")
TEMPLATE_PREFIX = "{{PREFIX}}-"
agents = {path.stem for pattern in LAYERS for path in pathlib.Path(".").glob(pattern)}
template = {path.stem for path in pathlib.Path("templates/profile/agents").glob("*.md")}
errors = []
for pattern in (*LAYERS, "templates/profile/agents/*.md"):
    for path in sorted(pathlib.Path(".").glob(pattern)):
        head = path.read_text(encoding="utf-8").partition("\n---\n")[0]
        for field, value in re.findall(r"(?m)^(depends_on|orchestrates):\s*(.*)$", head):
            try:
                names = json.loads(value)
            except ValueError:
                names = None
            if not isinstance(names, list):
                errors.append(f"{path.as_posix()}: {field} — список строк в формате [\"агент\"]")
                continue
            for name in names:
                # The profile template names its agents {{PREFIX}}-<role>
                known = template if name.startswith(TEMPLATE_PREFIX) else agents
                if name.removeprefix(TEMPLATE_PREFIX) not in known:
                    errors.append(f"{path.as_posix()}: {field} ссылается на агента {name}, которого нет в ките")
for error in errors:
    print(f"  ✗ {error}")
if not errors:
    print("  ✓ depends_on и orchestrates указывают на существующих агентов")
sys.exit(1 if errors else 0)
' || FAILURES=$((FAILURES + 1))

echo "▶ Агенты и скиллы профилей: команды из контракта, без npm, npx, pnpm, yarn"
"$PYTHON_BIN" -c '
import pathlib, re, sys
# The package manager is the team choice: agents take install, lint, test and the rest from .aikit/profiles.json
files = [*pathlib.Path("profiles").glob("*/agents/*.md"), *pathlib.Path("profiles").glob("*/skills/*/SKILL.md"), *pathlib.Path("templates/profile").glob("**/*.md")]
errors = []
for path in sorted(files):
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = re.search(r"(?<![\w./-])(npm|npx|pnpm|yarn) ", line)
        if match:
            errors.append(f"{path.as_posix()}:{number}: {match.group(1)} — возьми команду профиля из .aikit/profiles.json")
for error in errors:
    print(f"  ✗ {error}")
if not errors:
    print("  ✓ агенты и скиллы профилей не зовут менеджер пакетов напрямую")
sys.exit(1 if errors else 0)
' || FAILURES=$((FAILURES + 1))

echo "▶ git commit в агентах и скиллах — по режиму коммитов скилла git-commit"
"$PYTHON_BIN" -c '
import pathlib, re, sys
layers = ("base", "profiles/*", "packs/*")
patterns = ("agents/*.md", "skills/*/SKILL.md", "plugin-skills/*/SKILL.md")
files = [path for layer in layers for pattern in patterns for path in pathlib.Path(".").glob(f"{layer}/{pattern}")]
errors = []
for path in sorted(files):
    text = path.read_text(encoding="utf-8")
    if path.parent.name != "git-commit" and re.search(r"\bgit commit\b", text) and "git-commit" not in text:
        errors.append(f"{path.as_posix()}: есть git commit, но нет ссылки на скилл git-commit — сообщение по его правилам, вопрос пользователю по режиму commit (ask | auto) из .aikit/settings.json")
for error in errors:
    print(f"  ✗ {error}")
if not errors:
    print("  ✓ команды git commit следуют режиму коммитов")
sys.exit(1 if errors else 0)
' || FAILURES=$((FAILURES + 1))

echo "▶ Скиллы разработки кита: копии в .claude/skills и .agents/skills описаны одинаково"
"$PYTHON_BIN" -c '
import pathlib, re, sys
# Bodies may differ between runtimes, the name and description do not
def field(path, key):
    head = path.read_text(encoding="utf-8").partition("\n---\n")[0]
    match = re.search(rf"(?m)^{key}:\s*(.*)$", head)
    return match.group(1).strip() if match else None
claude = {path.parent.name: path for path in pathlib.Path(".claude/skills").glob("*/SKILL.md")}
codex = {path.parent.name: path for path in pathlib.Path(".agents/skills").glob("*/SKILL.md")}
errors = [f"скилл {name} есть только в {(claude.get(name) or codex.get(name)).parent.as_posix()}" for name in sorted(claude.keys() ^ codex.keys())]
for name in sorted(claude.keys() & codex.keys()):
    errors += [f"{claude[name].as_posix()} и {codex[name].as_posix()}: разный {key}" for key in ("name", "description") if field(claude[name], key) != field(codex[name], key)]
for error in errors:
    print(f"  ✗ {error}")
if not errors:
    print("  ✓ копии скиллов для Claude Code и Codex описаны одинаково")
sys.exit(1 if errors else 0)
' || FAILURES=$((FAILURES + 1))

if [[ "$FAILURES" -gt 0 ]]; then
  echo "✗ Статические проверки: ошибок — $FAILURES"
  exit 1
fi
echo "✓ Статические проверки пройдены"
