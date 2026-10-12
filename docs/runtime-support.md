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

Справочник по родным механизмам. Сверено с документацией 2026-10-12.

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
| Плагины / marketplace | есть | есть (свой формат) | npm-плагины |

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
| Хуки | ❌ (этап 4) | ❌ (этап 4) | ❌ (этап 4) |
| Запрет чтения `.env`, без соавторства | ✅ `.claude/settings.json` | ❌ | ❌ |
| Память `.aikit/memory/` | ✅ | ✅ | ✅ |
| Обновление | ✅ `update.sh` | ✅ `update-adapter-package.py` | ✅ `update-adapter-package.py` |
| Смена пресета и обновление | ✅ | ✅ файлы прошлой установки убираются | ✅ файлы прошлой установки убираются |
| Smoke-тест в CI | ✅ правила, скиллы, настройки, обновление | ✅ правила, скиллы, TOML агентов, обновление | ✅ правила, скиллы, агенты, обновление |
| Изоляция проекта | ✅ | ✅ ничего не пишется в `~/.codex` | ✅ |

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
| Хуки | Codex | Хуки не запускаются, пока пользователь не одобрит их через `/hooks` | В инструкции по установке — шаг «одобрить хуки» |
| Хуки | OpenCode | Нет конфигурации хуков, только плагины на JS/TS | Тонкий JS-плагин, который вызывает общий скрипт хука |
