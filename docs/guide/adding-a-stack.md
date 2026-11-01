# Как добавить стек

Профиль — папка `profiles/<name>/`, которая учит AIKit работать с одним стеком: Java + Spring, Go, Node.js, Flutter и т. д. Ядро кита (установщики, `/implement-feature`, `/security-check`, `tech-planner`) ничего не знает о конкретных стеках: всё, что ему нужно, оно читает из контракта профиля. Поэтому новый стек добавляется без правок ядра — только новой папкой в `profiles/`.

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
  "specialists": {
    "quality": {
      "agent": "spring-quality-analyst",
      "when": "нужна оценка покрытия тестами или технического долга (/coverage-check, /tech-debt)"
    }
  },
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
| `label`, `stack` | Название и стек для людей и для выбора профиля по задаче | `/implement-feature`, каталог |
| `role` | Часть системы: `backend`, `web` или своя (`mobile`, `mod`…). В мульти-профиле backend идёт первым — он фиксирует API | `/implement-feature`, `tech-planner` |
| `agents` | Агенты по ролям: ровно `architect`, `coder`, `tester`, `reviewer` | все оркестраторы |
| `specialists` | Дополнительные агенты: `{"<имя>": {"agent": "<агент>", "when": "<когда звать>"}}`. Специалист `quality` есть у каждого профиля — его зовут `/coverage-check` и `/tech-debt`. Необязательный специалист `security` проверяет то, что видно только со знанием стека, — его `/security-check` зовёт вместе с общим `security-auditor` (пример — `forge-1-12-java-security-auditor`) | `/implement-feature` |
| `pipelines` | Необязательные цепочки, кроме кода: `{"<имя>": {"when": "<когда>", "steps": ["<агент>", …]}}` | `/implement-feature` |
| `commands` | `install`, `lint`, `format`, `test` (обязательна), `build`, `run`. `{files}` — изменённые файлы. `run` запускает приложение в `/check-feature` | `/implement-feature`, `/fix-bug`, `/check-feature`, агенты, хуки |
| `actions` | Необязательно: кнопки блока «Действия проекта» в [AIKit Deck](commands.md#панель-aikit-deck): `{"<id>": {"label": "<кнопка>", "argv": ["./gradlew", "build"], "description": "<что делает>"}}`. `argv` — программа и аргументы, запускаются в папке профиля без shell и без модели, поэтому без `&&`, `|`, `>` и `{files}`. На Windows панель запускает их через `cmd /d /c`, `./gradlew` — как `.\gradlew.bat`. Кнопку «Обновить профиль» панель добавляет каждому профилю сама — в `actions` её не пишут (пример — `forge-1-12-java`) | AIKit Deck |
| `code_extensions` | Необязательно: расширения файлов кода (`[".java"]`). Хуки запускают `format` и `lint` только для них, а `test` — если менялись они. Без поля кодом считается любой файл в папке профиля | хуки |
| `root_markers` | Файлы, по которым установщик находит папку профиля в монорепо (`pom.xml`, `go.mod`, `package.json`…) | установщики |
| `path_signals` | Пути внутри папки профиля, по которым задача относится к этому профилю | `/implement-feature` |

При установке контракты всех подключённых профилей собираются в `.aikit/profiles.json` проекта и дополняются полем `root` — найденной папкой профиля. Команда проекта может править в этом файле `commands`, `actions` и `root`, обновление кита их не затрёт.

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
  RULES.md                — общие правила стека (с TODO)
  codex/
    agents/*.toml         — пять независимых агентов Codex
    catalog.json          — выходные блоки и метаданные Codex
  settings.json           — разрешения Claude Code на команды профиля (Bash(./mvnw *))
  agents/
    spring-architect.md   — выводит ARCHITECT_PLAN
    spring-coder.md       — CODER_RESULT
    spring-tester.md      — TESTER_RESULT
    spring-reviewer.md    — REVIEW_RESULT
    spring-quality-analyst.md — специалист quality: покрытие и техдолг, QUALITY_REPORT
```

Префикс агентов (`spring`) по умолчанию — последняя часть имени профиля; поменять можно флагом `--prefix`. Имена агентов и скиллов должны быть уникальны во всём ките — иначе профили нельзя будет подключить вместе.

## Шаг 2 — наполнить профиль знанием стека

Шаблон рабочий сразу, но агенты знают о стеке только строку `stack`. Ценность профиля — в том, что ты допишешь:

1. **`RULES.md`** — общие для runtime требования стека: структура проекта, слои, правила кода, именование, тесты, «динамическая экспертиза» (какой режим включает агент по типу файлов). Образец — `profiles/vue-nuxt/RULES.md`.
2. **Агенты** — независимо заполни `agents/*.md` для Claude и `codex/agents/*.toml` для Codex. У нативных TOML свои model и model_reasoning_effort, они не строятся из Markdown. Заполни разделы с `TODO`: что проектирует архитектор, обязательные пункты плана, правила реализации, тестовый стек, чек-лист ревьюера, команда покрытия и типичный техдолг стека у quality-аналитика. Формат блоков (`=== ARCHITECT_PLAN ===` … `=== END ARCHITECT_PLAN ===`) не меняй — по ним агенты передают работу друг другу. Уровень модели (`model:`) шаблон уже расставил: архитектор и ревьюер — `opus`, остальные — `sonnet`; совместимые модели OpenCode за уровнями — в `adapters/models.json`. Уровень усилий Claude Code (`effort:`) — тоже: архитектор `high`, остальные `medium`.
3. **Специалисты** (по желанию) — свои определения в `agents/` и `codex/agents/`, запись в `codex/catalog.json` и запись в `specialists` с условием `when`. Пример — `design-bridge` в `profiles/vue-nuxt/`.
4. **Пайплайны** (по желанию) — если профиль делает не только код (раздел «Пайплайны» ниже).
5. **Скиллы** (по желанию) — самостоятельные `codex/skills/<name>/SKILL.md` для Codex и `skills/<name>/SKILL.md` для частых задач стека (`/new-controller`, `/add-migration`). `description` пиши под автовызов: что делает + «Используй, когда…». Если скиллу нужен аргумент, добавь `argument-hint`: `<имя>` — обязательный, `[путь]` — необязательный, `[--флаг]` — переключатель; по нему панель AIKit Deck рисует поле ввода. Общие `/implement-feature`, `/security-check` уже работают с новым профилем.
6. **MCP-серверы** (по желанию) — `mcp.json` в формате `{"servers": {...}}`, как в `profiles/vue-nuxt/mcp.json`. Секреты — только через переменные окружения.

## Пайплайны: работа, кроме кода

Для каждого нового шага добавь Codex TOML и его выходной блок в `codex/catalog.json`, наряду с определением агента Claude.

Четыре роли (`architect`, `coder`, `tester`, `reviewer`) — обязательная цепочка кода. Если профилю нужна другая работа — модели и текстуры для мода, документация, локализация, — опиши её пайплайном: своими агентами в `agents/` и записью в контракте.

```json
"pipelines": {
  "asset": {
    "when": "нужны модель, текстура или звук для блока, предмета или моба",
    "steps": ["mc-art-director", "mc-model-maker", "mc-texture-artist", "mc-asset-reviewer"]
  }
}
```

- Шаги идут по порядку; каждый агент получает задачу и выходной блок предыдущего (`output_block` во frontmatter Claude или `codex/catalog.json` для Codex, например `ART_BRIEF` → `MODEL_RESULT` → `TEXTURE_RESULT`).
- Задача целиком подходит под `when` и не меняет код («нарисуй текстуру меча») — `/implement-feature` запускает только пайплайн.
- Фиче нужен и код, и пайплайн («добавь новую руду») — пайплайн идёт после архитектора, его результат получает кодер.
- Отличие от `specialists`: специалист — один агент, который дополняет цепочку кода; пайплайн — самостоятельная цепочка из нескольких агентов.

Агент работает текстом. Если шаг должен создать бинарный файл (PNG-текстуру, звук), дай агенту инструмент: скрипт в проекте, который он запускает, или MCP-сервер (ключи — только через переменные окружения).

## Шаг 3 — проверить

```bash
python3 scripts/build-plugins.py   # new-profile.py уже собрал плагин; повтори после правок агентов, скиллов и mcp.json
python3 scripts/generate-docs.py   # профиль появится в каталоге сайта документации
bash scripts/ci/static-checks.sh   # контракт полон, агенты существуют, имена уникальны, сайт и плагины собраны
bash scripts/ci/run-all.sh         # всё целиком, включая установку на тестовые проекты
```

Качество агентов и скиллов профиля проверяют [эвалы](developing-aikit.md#эвалы): заведи группу `evals/java-spring/` — маленький проект в `evals/fixtures/`, кейс генерации скиллом профиля и кейс ревью файла с заложенными ошибками (образцы — соседние группы). Дальше после каждой правки профиля гоняй только его группу — прогон тратит лимиты подписки, поэтому запуск вручную:

```bash
python3 scripts/run-evals.py java-spring --quick
```

Профиль — это и плагин маркетплейса: после слияния в `main` его ставят как `/plugin install java-spring@aikit` и подключают `/aikit:setup vue-nuxt+java-spring`.

Через установщик — отдельно или вместе с другими профилями:

```bash
bash .aikit-config/scripts/attach.sh java-spring
bash .aikit-config/scripts/attach.sh vue-nuxt+java-spring --pack devops
```

Если профиль будет частой комбинацией — добавь пресет: `presets/<name>.json` с полями `name`, `label`, `description`, `profiles`, `packs`.

## Паки и профиль

Пак (`packs/<name>/`) — набор агентов и скиллов, не привязанный к одному стеку (`devops`). Если в `pack.json` нет `compatible_profiles`, пак подходит к любому профилю, в том числе новому.
