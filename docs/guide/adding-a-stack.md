# Как добавить стек

Профиль — папка `profiles/<name>/`, которая учит AIKit работать с одним стеком: Java + Spring, Go, Node.js, Flutter и т. д. Ядро кита (установщики, `/implement-feature`, `/workflow`, `/security-check`, `workflow-runner`, `tech-planner`) ничего не знает о конкретных стеках: всё, что ему нужно, оно читает из контракта профиля. Поэтому новый стек добавляется без правок ядра — только новой папкой в `profiles/`.

## Что такое контракт профиля

Контракт — файл `profiles/<name>/profile.manifest.json`. Это договорённость между профилем и ядром: профиль обещает, что у него есть перечисленные агенты и команды, а ядро обещает работать с ними одинаково для любого стека.

```json
{
  "profile": "java-spring",
  "label": "Java Spring",
  "role": "backend",
  "stack": "Java 21, Spring Boot 3, JUnit 5",
  "agents": {
    "architect": "spring-architect",
    "coder": "spring-coder",
    "tester": "spring-tester",
    "reviewer": "spring-reviewer"
  },
  "specialists": {},
  "pipelines": {},
  "commands": {
    "install": "./mvnw dependency:resolve",
    "lint": "./mvnw checkstyle:check",
    "test": "./mvnw test",
    "build": "./mvnw package"
  },
  "code_extensions": [".java"],
  "root_markers": ["pom.xml"],
  "path_signals": ["src/main/java/", "src/test/java/"]
}
```

| Поле | Что значит | Кто читает |
|---|---|---|
| `profile` | Имя профиля, совпадает с папкой | установщики |
| `label`, `stack` | Название и стек для людей и для выбора профиля по задаче | `/implement-feature`, `workflow-runner`, каталог |
| `role` | Часть системы: `backend`, `web` или своя (`mobile`, `mod`…). В мульти-профиле backend идёт первым — он фиксирует API | `/implement-feature`, `tech-planner` |
| `agents` | Агенты по ролям: ровно `architect`, `coder`, `tester`, `reviewer` | все оркестраторы |
| `specialists` | Необязательные агенты: `{"<имя>": {"agent": "<агент>", "when": "<когда звать>"}}` | `/implement-feature`, `workflow-runner` |
| `pipelines` | Необязательные цепочки, кроме кода: `{"<имя>": {"when": "<когда>", "steps": ["<агент>", …]}}` | `/implement-feature`, `workflow-runner` |
| `commands` | `install`, `lint`, `format`, `test` (обязательна), `build`, `run`. `{files}` — изменённые файлы. `install` ставит зависимости в `/implement-feature --worktree`, `run` запускает приложение в `/check-feature` | `/implement-feature`, `/fix-bug`, `/check-feature`, агенты, хуки |
| `code_extensions` | Необязательно: расширения файлов кода (`[".java"]`). Хуки запускают `format` и `lint` только для них, а `test` — если менялись они. Без поля кодом считается любой файл в папке профиля | хуки |
| `root_markers` | Файлы, по которым установщик находит папку профиля в монорепо (`pom.xml`, `go.mod`, `package.json`…) | установщики |
| `path_signals` | Пути внутри папки профиля, по которым задача относится к этому профилю | `/implement-feature`, `workflow-runner` |

При установке контракты всех подключённых профилей собираются в `.aikit/profiles.json` проекта и дополняются полем `root` — найденной папкой профиля. Команда проекта может править в этом файле `commands` и `root`, обновление кита их не затрёт.

## Шаг 1 — создать профиль из шаблона

```bash
python3 scripts/new-profile.py java-spring --role backend --stack "Java 21, Spring Boot 3, JUnit 5" \
  --install "./mvnw dependency:resolve" --test "./mvnw test" --lint "./mvnw checkstyle:check" --build "./mvnw package" \
  --root-marker pom.xml --path-signal src/main/java/ --path-signal src/test/java/ \
  --code-extension .java
```

Скрипт берёт шаблон из `templates/profile/` и создаёт:

```text
profiles/java-spring/
  profile.manifest.json   — контракт
  CLAUDE.md               — правила стека (с TODO)
  settings.json           — разрешения Claude Code на команды профиля (Bash(./mvnw *))
  agents/
    spring-architect.md   — выводит ARCHITECT_PLAN
    spring-coder.md       — CODER_RESULT
    spring-tester.md      — TESTER_RESULT
    spring-reviewer.md    — REVIEW_RESULT
```

Префикс агентов (`spring`) по умолчанию — последняя часть имени профиля; поменять можно флагом `--prefix`. Имена агентов и скиллов должны быть уникальны во всём ките — иначе профили нельзя будет подключить вместе.

## Шаг 2 — наполнить профиль знанием стека

Шаблон рабочий сразу, но агенты знают о стеке только строку `stack`. Ценность профиля — в том, что ты допишешь:

1. **`CLAUDE.md`** — структура проекта, слои, правила кода, именование, тесты, «динамическая экспертиза» (какой режим включает агент по типу файлов). Образцы — `profiles/python-fastapi/CLAUDE.md`, `profiles/vue-nuxt/CLAUDE.md`.
2. **Агенты** — разделы с `TODO`: что проектирует архитектор, обязательные пункты плана, правила реализации, тестовый стек, чек-лист ревьюера. Формат блоков (`=== ARCHITECT_PLAN ===` … `=== END PLAN ===`) не меняй — по ним агенты передают работу друг другу.
3. **Специалисты** (по желанию) — свой агент в `agents/` и запись в `specialists` с условием `when`. Пример — `admin-expert` в `profiles/python-django/`.
4. **Пайплайны** (по желанию) — если профиль делает не только код (раздел «Пайплайны» ниже).
5. **Скиллы** (по желанию) — `skills/<name>/SKILL.md` для частых задач стека (`/new-controller`, `/add-migration`). `description` пиши под автовызов: что делает + «Используй, когда…». Общие `/implement-feature`, `/workflow`, `/security-check` уже работают с новым профилем.
6. **MCP-серверы** (по желанию) — `mcp.json` в формате `{"servers": {...}}`, как в `profiles/vue-nuxt/mcp.json`. Секреты — только через переменные окружения.

## Пайплайны: работа, кроме кода

Четыре роли (`architect`, `coder`, `tester`, `reviewer`) — обязательная цепочка кода. Если профилю нужна другая работа — модели и текстуры для мода, документация, локализация, — опиши её пайплайном: своими агентами в `agents/` и записью в контракте.

```json
"pipelines": {
  "asset": {
    "when": "нужны модель, текстура или звук для блока, предмета или моба",
    "steps": ["mc-art-director", "mc-model-maker", "mc-texture-artist", "mc-asset-reviewer"]
  }
}
```

- Шаги идут по порядку; каждый агент получает задачу и выходной блок предыдущего (`output_block` во frontmatter, например `ART_BRIEF` → `MODEL_RESULT` → `TEXTURE_RESULT`).
- Задача целиком подходит под `when` и не меняет код («нарисуй текстуру меча») — `/implement-feature` и `/workflow` запускают только пайплайн.
- Фиче нужен и код, и пайплайн («добавь новую руду») — пайплайн идёт после архитектора, его результат получает кодер.
- Отличие от `specialists`: специалист — один агент, который дополняет цепочку кода; пайплайн — самостоятельная цепочка из нескольких агентов.

Агент работает текстом. Если шаг должен создать бинарный файл (PNG-текстуру, звук), дай агенту инструмент: скрипт в проекте, который он запускает, или MCP-сервер (ключи — только через переменные окружения).

## Шаг 3 — проверить

```bash
python3 scripts/generate-docs.py   # профиль появится в каталоге сайта документации
bash scripts/ci/static-checks.sh   # контракт полон, агенты существуют, имена уникальны, сайт собран
bash scripts/ci/run-all.sh         # всё целиком, включая установку на тестовые проекты
```

Подключить к своему проекту — отдельно или вместе с другими профилями:

```bash
bash .aikit-config/scripts/attach.sh java-spring
bash .aikit-config/scripts/attach.sh vue-nuxt+java-spring --pack quality
```

Если профиль будет частой комбинацией — добавь пресет: `presets/<name>.json` с полями `name`, `label`, `description`, `profiles`, `packs`.

## Паки и профиль

Пак (`packs/<name>/`) — набор агентов и скиллов, не привязанный к одному стеку (`quality`, `devops`). Если в `pack.json` нет `compatible_profiles`, пак подходит к любому профилю, в том числе новому. Пак `ai` ограничен Python-профилями — чтобы подключить его к новому стеку, добавь профиль в его `compatible_profiles`.
