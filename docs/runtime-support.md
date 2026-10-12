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
| Slash-команды (старый формат) | `.claude/commands/*.md` | нет в проекте — заменены скиллами | `.opencode/commands/` |
| Сабагенты | `.claude/agents/*.md` | `.codex/agents/*.toml` (`name`, `description`, `developer_instructions`) | `.opencode/agents/*.md` (`description`, `mode: subagent`) |
| MCP-серверы | `.mcp.json` | `[mcp_servers.*]` в `.codex/config.toml` (только для доверенных проектов) | `"mcp"` в `opencode.json` |
| Секреты для MCP | `${VAR}` в `.mcp.json` | `env_vars = ["VAR"]`, `bearer_token_env_var` | `{env:VAR}` |
| Хуки | `hooks` в `.claude/settings.json` | `.codex/hooks.json` или `[hooks]` в `.codex/config.toml`; нужно одобрить через `/hooks` | JS/TS-плагин в `.opencode/plugins/` (`tool.execute.before` / `after`, `session.idle`) |
| Запреты (permissions) | `permissions` в `.claude/settings.json` | `sandbox_mode`, `approval_policy` в `config.toml` | `permission` в `opencode.json` и у агента |
| Плагины / marketplace | есть | есть (свой формат) | npm-плагины |

---

## 2. Что AIKit ставит сейчас

Состояние на 2026-10-12, проверено установкой пресета `frontend-team` на пустой проект.

| Возможность | Claude Code (`attach.sh`) | Codex | OpenCode |
|---|---|---|---|
| Установка всех пресетов | ✅ | ⚠️ `fullstack-web` падает (1.3) | ⚠️ `fullstack-web` падает (1.3) |
| Правила проекта | ✅ `CLAUDE.md` | ❌ нет `AGENTS.md` — Codex не видит правил (2.0) | ❌ нет `AGENTS.md` / `CLAUDE.md` (2.0) |
| Скиллы | ⚠️ только `git-commit`, `git-branch`; остальное — команды (2.1) | ❌ лежат в `.codex/skills/`, Codex их не читает (2.0) | ❌ лежат в `.aikit/skills/`, OpenCode их не читает (2.0) |
| Сабагенты | ✅ `.claude/agents/` | ⚠️ `.codex/agents/*.toml` в верном формате; лишние таблицы `[agents."name"]` в `config.toml` — проверить (2.0) | ❌ в `.opencode/agents/` только README (2.0) |
| MCP-серверы | ⚠️ в `.claude/settings.json`, который попадает в `.gitignore` (2.3) | ❌ (2.3) | ❌ (2.3) |
| Хуки | ❌ (этап 4) | ❌ (этап 4) | ❌ (этап 4) |
| Запрет чтения `.env`, без соавторства | ✅ `.claude/settings.json` | ❌ | ❌ |
| Память `.aikit/memory/` | ✅ | ✅ | ✅ |
| Обновление | ✅ `update.sh` | ✅ `update-adapter-package.py` | ✅ `update-adapter-package.py` |
| Smoke-тест в CI | ✅ | ❌ (1.4) | ❌ (1.4) |

---

## 3. Известные ограничения

Функции, которые в каком-то runtime нельзя сделать так же, как в Claude Code, и чем они заменены.

| Функция | Runtime | Ограничение | Замена |
|---|---|---|---|
| Slash-команды | Codex | Проектных slash-команд нет | Скиллы: `$name` или автовызов |
| MCP из проекта | Codex | `.codex/config.toml` применяется только в доверенных проектах | В инструкции по установке — шаг «отметить проект доверенным» |
| Хуки | Codex | Хуки не запускаются, пока пользователь не одобрит их через `/hooks` | В инструкции по установке — шаг «одобрить хуки» |
| Хуки | OpenCode | Нет конфигурации хуков, только плагины на JS/TS | Тонкий JS-плагин, который вызывает общий скрипт хука |
