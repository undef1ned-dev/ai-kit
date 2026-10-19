# Разработка AIKit

Как устроен репозиторий кита, какие правила держат его в порядке и как проверить изменения. Страница для тех, кто развивает сам AIKit, — людей и AI-агентов. Перед изменением кита прочитай её целиком.

## Принципы

1. **Источник один.** Агенты, скиллы, правила и MCP-серверы описываются один раз — в `base/`, `profiles/`, `packs/`. В формат каждого runtime их раскладывают установщики и генератор плагинов. Файлы под конкретный runtime руками не пишут.
2. **Ядро не знает стеков.** Базовые скиллы и оркестраторы не называют агентов профилей и стековые команды. Всё стековое они берут из `.aikit/profiles.json`, а он собирается из контрактов. Это проверяет статическая проверка.
3. **Каждая задача — для всех runtime.** Задача закрыта, когда сделана для Claude Code и Codex. Для OpenCode она сделана или явно отмечена как невозможная в [docs/runtime-support.md](../runtime-support.md).
4. **Имена уникальны во всём ките.** Нет двух агентов или двух скиллов с одним именем — поэтому любые профили и паки ставятся вместе без переименований.
5. **Минимальный diff.** Попутно не рефакторить. Одна задача — один коммит.

## Карта репозитория

| Путь | Что это |
|---|---|
| `base/` | Ядро: `CLAUDE.md` (базовые правила), `agents/`, `skills/<name>/SKILL.md`, `hooks/` (скрипт хуков и плагин OpenCode), `settings.json`, `mcp.json`, `PRODUCT.md` (шаблон), `memory/` (шаблон памяти) |
| `base/plugin-skills/` | Скиллы только для плагина ядра: `setup` подключает проект (`/aikit:setup`) |
| `profiles/<name>/` | Профиль стека: `profile.manifest.json` (контракт), `CLAUDE.md`, `agents/`, `skills/`, `settings.json`, `mcp.json`; `.claude-plugin/` и `.codex-plugin/` — манифесты плагина (генерируются) |
| `packs/<name>/` | Пак: `pack.json`, `agents/`, `skills/`, `mcp.json`, манифесты плагина |
| `.claude-plugin/`, `.codex-plugin/` в корне | Маркетплейс `aikit` (`marketplace.json`, его читают и Claude Code, и Codex) и манифесты плагина ядра: корень плагина `aikit` — весь репозиторий. Генерируются `scripts/build-plugins.py` |
| `presets/*.json` | Пресеты: `name`, `label`, `description`, `profiles`, `packs` |
| `templates/profile/` | Шаблон нового профиля для `scripts/new-profile.py` |
| `adapters/<runtime>/` | Описание адаптера (`adapter.manifest.json`) и шаблоны файлов runtime |
| `scripts/` | Установщики, генераторы, общие Python-модули |
| `scripts/lib/` | Общие части `attach.sh` и `update.sh`: скиллы, MCP, контракты |
| `scripts/ci/` | Проверки: статические и smoke-тесты установки |
| `docs/guide/` | Документация в Markdown — источник сайта |
| `docs/site/` | Сайт документации: HTML собирается, `assets/site.css` и `site.js` пишутся руками |
| `docs/roadmap.md` | План развития — что делаем и в каком порядке |
| `docs/runtime-support.md` | Матрица возможностей по runtime |
| `docs/research/` | Исследования, на которых основан roadmap |
| `.github/workflows/` | CI на PR (`ci.yml`), релиз по тегу (`release.yml`), публикация сайта на GitHub Pages (`pages.yml`) |
| `CLAUDE.md` в корне | Правила для работы в этом репозитории — **копия** `base/CLAUDE.md` и правил `vue-nuxt`. Правь источники |
| `marketplace/` | Наследие прежней схемы дистрибуции, не используется. Маркетплейс плагинов — `.claude-plugin/marketplace.json` |

## Скрипты

| Скрипт | Что делает |
|---|---|
| `scripts/attach.sh` | Ставит кит в проект для Claude Code |
| `scripts/update.sh` | Обновляет установку Claude Code |
| `scripts/install-adapter-package.py` | Ставит кит для Codex или OpenCode (`build-adapter-package.py` собирает пакет) |
| `scripts/update-adapter-package.py` | Обновляет установку Codex или OpenCode |
| `scripts/profile_contract.py` | Собирает `.aikit/profiles.json`: контракты, поиск `root`, сохранение правок проекта |
| `scripts/mcp_config.py` | Пишет MCP-серверы в `.mcp.json`, `.codex/config.toml`, `opencode.json` |
| `scripts/hooks_config.py` | Копирует `base/hooks/aikit_hook.py` в `.aikit/hooks/` и подключает его: `hooks` в `.claude/settings.json`, `.codex/hooks.json`, плагин OpenCode |
| `scripts/build-plugins.py` | Собирает маркетплейс и манифесты плагинов Claude Code и Codex из `base/`, `profiles/`, `packs/`; `--check` — проверка в CI |
| `scripts/plugin-init.py` | Подключает проект к киту, установленному плагинами: блок правил, `.aikit/profiles.json`, память, настройки Claude Code или агенты Codex. Его вызывает скилл `/aikit:setup` |
| `scripts/new-profile.py` | Создаёт профиль из шаблона и пересобирает плагины ([Как добавить стек](adding-a-stack.md)) |
| `scripts/generate-docs.py` | Собирает сайт `docs/site/` из `docs/guide/` и исходников кита |
| `scripts/resolve-preset.py`, `preset_utils.py` | Разбор пресетов |
| `scripts/memory_paths.py` | Структура командной памяти `.aikit/memory/` |
| `scripts/release_utils.py`, `changelog_since.py` | Версия и changelog для релиза и `update.sh` |

## Как добавить…

### Агента

Файл `<слой>/agents/<name>.md`, где слой — `base`, `profiles/<p>` или `packs/<p>`. Frontmatter: `name` (совпадает с именем файла), `description` (что делает и когда звать), `tools`, при необходимости `output_block`, `example_prompt`. Можно начать с `/create-agent`. Агент профиля в одной из четырёх ролей прописывается в `agents` контракта, специалист — в `specialists`, шаг пайплайна — в `pipelines`.

### Скилл

Папка `<слой>/skills/<name>/SKILL.md`. `description` пиши под автовызов: что делает и «Используй, когда…». Скилл с побочными эффектами помечай `disable-model-invocation: true`. Можно начать с `/create-skill`. Новый скилл ядра добавь в [Команды](commands.md) — иначе проверка документации упадёт.

### Профиль

`python3 scripts/new-profile.py …` и дальше по [Как добавить стек](adding-a-stack.md).

### Пак

Папка `packs/<name>/` с `pack.json`: `name`, `label`, `description`, `agents`, `skills` и, если пак подходит не ко всем стекам, `compatible_profiles`. Затем `python3 scripts/build-plugins.py` — пак станет плагином маркетплейса.

### Пресет

`presets/<name>.json`: `name`, `label`, `description`, `profiles`, `packs`. Smoke-тесты CI сами прогоняют каждый пресет.

### Хук

Логика всех хуков — в `base/hooks/aikit_hook.py`: один обработчик на событие (`PreToolUse`, `PostToolUse`, `Stop`, `SessionStart`), вход — JSON в формате Claude Code и Codex. Плагин `base/hooks/opencode-plugin.js` переводит события OpenCode в тот же формат. Новое событие — запись в `EVENTS` в `scripts/hooks_config.py` и обработчик в скрипте. Скрипт без зависимостей, Python 3.9+. Каждое правило — сценарий в `scripts/ci/test-hooks.py`.

### MCP-сервер

`mcp.json` слоя в формате `{"servers": {...}}`. Версию пакета закрепляй (`@1.2.3`, не `@latest`). Секреты — только переменные окружения: `${VAR}`. После правки пересобери плагины: `python3 scripts/build-plugins.py`.

## Плагины и разработка на самом себе

- Маркетплейс и манифесты плагинов генерируются из источников: поменял агентов, скиллы, MCP, хуки или добавил профиль — запусти `python3 scripts/build-plugins.py` и закоммить результат. Статическая проверка сравнивает манифесты с источниками.
- Агенты, скиллы и хуки кита в этом репозитории не копируются в `.claude/` — их дают плагины прямо из рабочей копии. Для разработки запускай Claude Code с плагином ядра:

  ```bash
  claude --plugin-dir .
  ```

  Изменения в `base/` подхватываются после перезапуска сессии. Профиль или пак добавляются ещё одним флагом: `--plugin-dir profiles/vue-nuxt`.
- Проверить установку так, как её видит пользователь, — локальный маркетплейс: `/plugin marketplace add ./` и `/plugin install aikit@aikit`.
- `claude plugin validate .` проверяет маркетплейс и манифесты по схеме Claude Code. Предупреждения про `CLAUDE.md` в корне плагина и отсутствие `version` ожидаемы: версия не задана намеренно, чтобы плагины обновлялись с каждым коммитом в `main`.

## Документация

- Текст правится только в Markdown: `docs/guide/*.md`, `docs/roadmap.md`, `docs/runtime-support.md`.
- После правки собери сайт и закоммить `docs/site/` вместе с Markdown:

  ```bash
  python3 scripts/generate-docs.py
  ```

- После слияния в `main` workflow `.github/workflows/pages.yml` публикует `docs/site/` на GitHub Pages: https://undef1ned-dev.github.io/ai-kit/.
- Ссылки на файлы вне сайта (исходники агентов, скриптов) генератор ведёт на GitHub, в ветку `main`.
- Порядок страниц и меню задаёт список `PAGES` в `scripts/generate-docs.py`. Новая страница — новая запись в нём.
- Страница «Каталог профилей» строится из `base/`, `profiles/`, `packs/` и `presets/`. Новый агент или скилл появится в каталоге сам — нужно только пересобрать сайт.
- Ссылки между страницами пиши на `.md`-файлы (`[Термины](glossary.md#агент)`): на GitHub они работают как есть, на сайте генератор заменит их на `.html`. Битая ссылка или якорь — ошибка проверки.
- Компоненты сайта, которые на GitHub выглядят обычным Markdown:
  - `<!-- cards -->` перед списком `[Заголовок](ссылка) — текст` — сетка карточек;
  - `<!-- chain -->` перед списком `**имя** — текст` — схема со стрелками;
  - `<!-- steps -->` перед нумерованным списком — шаги;
  - `> [!NOTE]`, `> [!TIP]`, `> [!IMPORTANT]`, `> [!WARNING]` — выделенные блоки.
- Изменил поведение кита — обнови документацию в том же PR: страницу, которой это касается, [Известные ошибки](known-issues.md), строку в [roadmap](../roadmap.md) и матрицу [runtime](../runtime-support.md).

## Проверки

Все проверки CI одной командой, локально:

```bash
bash scripts/ci/run-all.sh
```

Запускай её перед каждым коммитом, который меняет скрипты, агентов, скиллы или контракты. Минуты CI ограничены, поэтому лучше поймать ошибку локально.

| Проверка | Что ловит |
|---|---|
| `scripts/ci/static-checks.sh` | Синтаксис `*.sh`, `*.py`, `*.json`; каталог видит все скиллы; контракты профилей полные и ссылаются на существующих агентов (роли, специалисты, пайплайны); ядро не называет агентов профилей; имена агентов и скиллов уникальны; сайт документации собран из актуальных исходников и без битых ссылок; манифесты плагинов актуальны; сценарии хуков (`scripts/ci/test-hooks.py`) |
| `scripts/ci/smoke-attach.sh <preset>` | `attach.sh` и `update.sh --auto` на пустом проекте, хуки подключены и не задваиваются |
| `scripts/ci/smoke-adapter.sh <codex\|opencode> <preset>` | Установка и обновление адаптера; файлы, которые реально читает runtime, хуки |
| `scripts/ci/smoke-plugin.sh <preset>` | Подключение проекта к плагинам (`plugin-init.py`) для Claude Code и Codex: блок правил один и сохраняет текст команды, настройки и плагины, агенты Codex, смена профилей |
| `scripts/ci/smoke-new-profile.sh` | Профиль из шаблона ставится без правок ядра, вместе с пайплайном, в монорепо |

CI (`.github/workflows/ci.yml`) запускает то же самое на Linux и Windows.

### Windows

- Нужна команда `python3` — см. [Известные ошибки](known-issues.md#windows-нет-команды-python3).
- Вывод скриптов с кириллицей: `export PYTHONIOENCODING=utf-8`.
- Скрипты пишут файлы с переводом строки `\n`. Не сохраняй `.sh` с CRLF — bash на них падает.

## Git

- Ветки — по Conventional Branch: `feat/…`, `fix/…`, `docs/…`, `chore/…` (скилл `git-branch`).
- Коммиты — по Conventional Commits, описание на русском: `feat(profiles): …` (скилл `git-commit`).
- Без `Co-Authored-By` и приписок «Generated with» — ни в коммитах, ни в описаниях PR.
- Один этап roadmap — один PR в `main`.

## Порядок работы над задачей

<!-- steps -->
1. Найди задачу в [roadmap](../roadmap.md) и прочитай связанные разделы этой документации.
2. Создай ветку от свежего `main`.
3. Сделай изменение в источниках (`base/`, `profiles/`, `packs/`, `scripts/`), не в копиях.
4. Обнови документацию: Markdown и `python3 scripts/generate-docs.py`.
5. Отметь задачу в roadmap и обнови матрицу runtime, если что-то поменялось для какого-то runtime.
6. `bash scripts/ci/run-all.sh` — всё зелёное.
7. Коммит, PR с описанием «что сделано и зачем».
