# Поддержка runtime

Какие возможности AIKit работают в каждом AI-агенте, где отличия и чего нет.
Обновляется в каждой задаче roadmap, которая добавляет или меняет функционал (см. принцип в [roadmap.md](roadmap.md)).

Приоритет: **Claude Code** и **Codex** — основные, OpenCode — переносим всё, что позволяет runtime.

GLM отдельно не поддерживается: это модель, а не агент — её можно запускать через любой из этих runtime, и кит будет работать так же, как в нём.

Обозначения:

- ✅ работает;
- ⚠️ работает частично или иначе — см. примечание;
- ❌ не сделано в AIKit, хотя runtime умеет — задача в roadmap;
- 🚫 runtime этого не умеет — нужна замена или функция недоступна;

---

## 1. Что умеет каждый runtime

Справочник по родным механизмам. Сверено с документацией 2026-10-12, плагины — 2026-10-19.

| Возможность | Claude Code | Codex | OpenCode |
|---|---|---|---|
| Правила проекта | `CLAUDE.md` | `AGENTS.md` | `AGENTS.md` (если его нет — `CLAUDE.md`) |
| Скиллы `<name>/SKILL.md` | `.claude/skills/` | `.agents/skills/` | `.opencode/skills/`, а также `.claude/skills/` и `.agents/skills/` |
| Вызов скилла | `/name` или автоматически по `description` | `$name`, `/skills` или автоматически по `description` | автоматически по `description` |
| Запрет автовызова скилла | `disable-model-invocation: true` во frontmatter | `policy.allow_implicit_invocation: false` в `<skill>/agents/openai.yaml` | нет в самом скилле (только `permission` в `opencode.json`) |
| Аргументы скилла | `$ARGUMENTS` подставляется | не подставляется — задача берётся из сообщения | не подставляется |
| Slash-команды (старый формат) | `.claude/commands/*.md` | нет в проекте — заменены скиллами | `.opencode/commands/` |
| Сабагенты | `.claude/agents/*.md` | `.codex/agents/*.toml` (`name`, `description`, `developer_instructions`) | `.opencode/agents/*.md` (`description`, `mode: subagent`) |
| MCP-серверы | `.mcp.json` | `[mcp_servers.*]` в `.codex/config.toml` (только для доверенных проектов) | `"mcp"` в `opencode.json` |
| Секреты для MCP | `${VAR}` в `.mcp.json` | `env_vars = ["VAR"]`, `bearer_token_env_var` | `{env:VAR}` |
| Хуки | `hooks` в `.claude/settings.json` | `.codex/hooks.json` или `[hooks]` в `.codex/config.toml`; нужно одобрить через `/hooks` | JS/TS-плагин в `.opencode/plugins/` (`tool.execute.before` / `after`, `session.idle`) |
| Запреты (permissions) | `permissions` в `.claude/settings.json` | `sandbox_mode`, `approval_policy` в `config.toml` | `permission` в `opencode.json` и у агента |
| Плагины / marketplace | `.claude-plugin/plugin.json`, `marketplace.json`: скиллы, агенты, хуки, MCP | `.codex-plugin/plugin.json`: скиллы, хуки, MCP — **без агентов**; маркетплейс читает и `.claude-plugin/marketplace.json` | npm-плагины |
| Имена из плагина | скилл `/плагин:имя` (и `/имя`, если не занято), агент — только `плагин:имя` | скилл `$имя` | — |

---

## 2. Что AIKit ставит сейчас

Состояние на 2026-10-12, проверено smoke-тестами всех пресетов (`scripts/ci/run-all.sh`).

| Возможность | Claude Code (`attach.sh`) | Codex | OpenCode |
|---|---|---|---|
| Установка всех пресетов | ✅ | ✅ | ✅ |
| Правила проекта | ✅ `CLAUDE.md` | ✅ блок AIKit в `AGENTS.md`, текст пользователя вне блока сохраняется | ✅ тот же `AGENTS.md` |
| Скиллы | ✅ `.claude/skills/<name>/SKILL.md` — все скиллы base, профилей и паков | ✅ `.agents/skills/<name>/SKILL.md` | ✅ `.agents/skills/<name>/SKILL.md` |
| Скиллы только по явному вызову (`capture-memory`, `optimize-memory`, `workflow`, `improve-aikit`) | ✅ `disable-model-invocation` | ✅ `agents/openai.yaml` | ⚠️ могут сработать автоматически |
| Старые команды прежних версий кита | ✅ убираются из `.claude/commands/` при обновлении, свои команды пользователя остаются | ✅ `.codex/commands/` убирается | — |
| Сабагенты | ✅ `.claude/agents/` | ✅ `.codex/agents/*.toml` (проект должен быть доверенным) | ✅ `.opencode/agents/*.md`, `mode: subagent` |
| MCP-серверы | ✅ `.mcp.json` | ✅ блок AIKit в `.codex/config.toml` (проект должен быть доверенным) | ✅ раздел `mcp` в `opencode.json` |
| MCP: один источник, версии закреплены, без секретов в файлах | ✅ `mcp.json` в base, профилях и паках | ✅ | ✅ |
| MCP: свои серверы пользователя сохраняются при обновлении | ✅ | ✅ | ✅ |
| Figma, Sentry — официальные удалённые MCP с входом через OAuth | ✅ | ✅ `codex mcp login <name>` | ⚠️ Figma пускает только клиентов из своего каталога |
| `.claude/settings.json` хранится в git | ✅ правило в `.gitignore` от прежних версий убирается | — | — |
| Контракты профилей в проекте (`.aikit/profiles.json`), правки команд сохраняются при обновлении | ✅ | ✅ | ✅ |
| Общий `/implement-feature` и `workflow-runner` берут агентов и команды из `.aikit/profiles.json` | ✅ | ✅ | ✅ |
| Монорепо: папка каждого профиля (`root`) находится при установке, команды запускаются в ней | ✅ | ✅ | ✅ |
| Новый профиль из шаблона (`scripts/new-profile.py`) ставится без правок ядра | ✅ | ✅ | ✅ (не проверено smoke) |
| Пайплайны профиля (`pipelines`) в `/implement-feature` и `workflow-runner` | ✅ | ✅ | ✅ |
| `/implement-feature`: тестировщик и ревьюер параллельно, линтер — пока они работают | ✅ фоновые сабагенты | ✅ несколько сабагентов, ожидание всех | ✅ несколько сабагентов в одном сообщении |
| `/implement-feature --worktree`: работа в git worktree от текущей ветки, перенос по согласию | ✅ | ✅ | ✅ |
| `/implement-feature --tdd`, `/fix-bug`: сначала падающий тест | ✅ | ✅ | ✅ |
| Общий ревью-шаг | ✅ встроенный `/code-review` + чек-лист ревьюера профиля | ⚠️ общий проход делает ревьюер профиля | ⚠️ общий проход делает ревьюер профиля |
| `/check-feature`: запуск `run` и проверка в браузере или запросами | ✅ | ✅ | ✅ |
| Хук: `format`, `lint` и `test` для файлов в worktree — в папке профиля внутри worktree | ✅ | ✅ | ✅ |
| Хуки: общий скрипт `.aikit/hooks/aikit_hook.py` | ✅ `hooks` в `.claude/settings.json` | ✅ `.codex/hooks.json` (нужно одобрить в `/hooks`) | ⚠️ плагин `.opencode/plugins/aikit-hooks.js` |
| Хук: запрет записи `.env` и секретов, `git add .env` | ✅ | ✅ | ✅ |
| Хук: коммиты по Conventional Commits без соавторства, ветки по Conventional Branch | ✅ | ✅ | ✅ |
| Хук: `format` и `lint` профиля после правки | ✅ замечания — в контекст агента | ✅ | ⚠️ замечания дописываются к выводу инструмента |
| Хук: `test` профиля, когда агент закончил | ✅ упавшие тесты продолжают работу | ✅ | ⚠️ упавшие тесты отправляются в сессию новым сообщением |
| Хук: память и `PRODUCT.md` в начале сессии | ✅ | ✅ | ✅ через `instructions` в `opencode.json` |
| Хуки пользователя сохраняются при обновлении | ✅ | ✅ | — |
| Запрет чтения `.env` | ✅ `.claude/settings.json` | ❌ | ❌ |
| Без соавторства в коммитах | ✅ `attribution` в `.claude/settings.json` и хук | ✅ хук | ✅ хук |
| Командная память `.aikit/memory/` (решения, паттерны, коррекции агентов), агенты читают её перед работой | ✅ | ✅ | ✅ |
| `/capture-memory`: коммит и PR по желанию, PR через `gh` (GitHub) или `glab` (GitLab) | ✅ | ✅ | ✅ |
| Личная память runtime отделена от командной | ✅ auto memory — личное, `.aikit/memory/` — командное | ✅ | ✅ |
| Обновление | ✅ `update.sh` | ✅ `update-adapter-package.py` | ✅ `update-adapter-package.py` |
| Смена пресета и обновление | ✅ | ✅ файлы прошлой установки убираются | ✅ файлы прошлой установки убираются |
| Smoke-тест в CI | ✅ правила, скиллы, настройки, обновление | ✅ правила, скиллы, TOML агентов, обновление | ✅ правила, скиллы, агенты, обновление |
| Изоляция проекта | ✅ | ✅ ничего не пишется в `~/.codex` | ✅ |

### Установка плагинами

Маркетплейс `aikit` — `.claude-plugin/marketplace.json` в корне репозитория: ядро `aikit`, по плагину на профиль и пак. Проект подключает скилл `/aikit:setup` (`scripts/plugin-init.py`). Проверено smoke-тестами (`scripts/ci/smoke-plugin.sh`) и `claude plugin validate`; Claude Code — вживую (`--plugin-dir`), Codex — только по формату.

| Возможность | Claude Code | Codex | OpenCode |
|---|---|---|---|
| Маркетплейс и плагины ядра, профилей, паков | ✅ `/plugin marketplace add undef1ned-dev/ai-kit` | ⚠️ `codex plugin marketplace add undef1ned-dev/ai-kit`, не проверено вживую | 🚫 остаётся установщик |
| Скиллы | ✅ из плагинов | ⚠️ из плагинов | — |
| Агенты | ✅ из плагинов, имя с префиксом плагина | ⚠️ плагины Codex не поставляют агентов — `/aikit:setup` пишет `.codex/agents/*.toml` | — |
| Хуки | ✅ из плагина ядра, только в проектах с `.aikit/` | ⚠️ из плагина ядра (`${PLUGIN_ROOT}`), не проверено вживую | — |
| MCP-серверы | ✅ из плагинов | ⚠️ из плагинов | — |
| Правила проекта | ✅ блок AIKit в `CLAUDE.md` | ✅ блок AIKit в `AGENTS.md` | — |
| Права, запрет `.env`, без соавторства, плагины для команды | ✅ `.claude/settings.json`: `permissions`, `attribution`, `extraKnownMarketplaces`, `enabledPlugins` | ⚠️ только хук; маркетплейс каждый добавляет сам | — |
| Обновление | ✅ `/plugin marketplace update aikit` — плагины без `version` обновляются с каждым коммитом в `main` | ✅ `codex plugin marketplace upgrade` | — |

### Эвалы

Эталонные задачи `evals/` и раннер `scripts/run-evals.py` — только для разработки кита, запуск вручную ([Разработка AIKit](guide/developing-aikit.md#эвалы)).

| Возможность | Claude Code | Codex | OpenCode |
|---|---|---|---|
| Прогон кейсов | ✅ `claude plugin eval`, проверено вживую | ⚠️ `codex exec` через раннер, проверено на подставном `codex` | 🚫 нет неинтерактивного прогона с оценкой — не делаем |
| Оценщики | ✅ все типы | ⚠️ `regex` и `file_exists`; `tool_used` и судья-модель пропускаются | — |
| Сравнение с прогоном без кита (`Δ`) | ✅ | 🚫 | — |

---

## 3. Известные ограничения

Функции, которые в каком-то runtime нельзя сделать так же, как в Claude Code, и чем они заменены.

| Функция | Runtime | Ограничение | Замена |
|---|---|---|---|
| Slash-команды | Codex | Проектных slash-команд нет (глобальные `~/.codex/prompts` устарели и общие для всех проектов — кит их не пишет) | Скиллы: `$name` или автовызов |
| Агенты из проекта | Codex | `.codex/agents/` применяется только в доверенных проектах | В инструкции `.codex/AIKIT.md` — шаг «отметить проект доверенным» |
| Правила и скиллы | Codex, OpenCode | Тексты написаны в синтаксисе Claude Code (`/name`, местами `.claude/`) | В начале блока AIKit в `AGENTS.md` объяснено, что `/name` — это скилл (`$name` в Codex); пути `.claude/agents/` и `.claude/skills/` в скиллах заменяются на пути runtime |
| `$ARGUMENTS` в скиллах | Codex, OpenCode | Не подставляется | При установке заменяется на «(задача из запроса пользователя)» |
| Запрет автовызова скилла | OpenCode | Нет поля в `SKILL.md` | Пока нет; скиллы с побочными эффектами сами просят подтверждения |
| MCP из проекта | Codex | `.codex/config.toml` применяется только в доверенных проектах | В `.codex/AIKIT.md` — шаг «отметить проект доверенным» |
| Секреты для MCP | Codex | Переменную можно только пробросить под тем же именем (`env_vars`), переименовать нельзя | В `mcp.json` указывать переменную под тем именем, которое читает сам сервер |
| `opencode.json` с комментариями | OpenCode | Установщик читает только JSON без комментариев | Если файл не разобран — MCP не добавляются, выводится предупреждение |
| Хуки | Codex | Хуки не запускаются, пока пользователь не одобрит их через `/hooks`; изменённые хуки нужно одобрить снова | В `.codex/AIKIT.md` и инструкции по установке — шаг «одобрить хуки» |
| Хуки | Codex | На Windows команда хука — `python`, не `python3` (`commandWindows`) | `python` должен быть Python 3.9+ |
| Хуки | OpenCode | Нет конфигурации хуков, только плагины на JS/TS | Плагин `.opencode/plugins/aikit-hooks.js` вызывает общий скрипт хука |
| Хуки после правки и в конце ответа | OpenCode | Плагин не может добавить контекст к ответу так, как `additionalContext` в Claude Code и Codex | Замечания линтера дописываются к выводу инструмента; упавшие тесты — новым сообщением в сессию (`session.idle` → `client.session.prompt`). Не проверено на живом OpenCode |
| Общий ревью-шаг | Codex, OpenCode | Встроенное ревью (`/review`) агент не может вызвать сам | Ревьюер профиля делает общий проход (корректность, ошибки, безопасность) перед своим чек-листом; `/review` можно запустить вручную |
| Worktree для `/implement-feature` | Claude Code | Встроенная изоляция сабагентов (`isolation: worktree`) ответвляется от ветки по умолчанию, а не от текущей, и даёт каждому агенту свой worktree | Оркестратор сам создаёт один worktree от `HEAD` (`git worktree add`) — одинаково во всех runtime |
| Проверка UI в `/check-feature` | все | Нужен браузерный инструмент | Playwright MCP профиля или встроенный браузер runtime; без них — проверка запросами |
| Агенты в плагине | Codex | Манифест плагина Codex не поддерживает агентов | `/aikit:setup` (`plugin-init.py --runtime codex`) пишет агентов ядра, профилей и паков в `.codex/agents/*.toml`; при смене профилей лишние убираются |
| Имена агентов из плагина | Claude Code | Агент плагина находится только по имени с префиксом: `vue-nuxt:vue-coder`, а в `.aikit/profiles.json` записано `vue-coder` | В блоке правил `CLAUDE.md` — правило префикса; если агент вызван без префикса, Claude Code в ошибке перечисляет правильные имена |
| Хуки плагина | Claude Code, Codex | Хуки плагина включены во всех проектах пользователя | Хук с флагом `--plugin` работает только в проектах с `.aikit/` |
| Эвалы | Claude Code | В изолированном прогоне не грузится `CLAUDE.md` проекта с блоком AIKit — скиллы и агенты профиля выбираются только по их `description` | Так эвалы мерят вклад самих плагинов; найденные провалы автовызова — задачи на описания скиллов и агентов |
| Эвалы | Codex | Нет команды для эвалов; скилл или агент в выводе `codex exec` не отличить | Раннер оценивает только общие проверки: ответ, файлы, трассу |
| Контекст в начале сессии | OpenCode | Плагин не добавляет контекст при старте сессии | `.aikit/memory/INDEX.md` и `PRODUCT.md` в `instructions` в `opencode.json` — OpenCode читает их сам |
