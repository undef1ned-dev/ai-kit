# AIKit

AIKit — переиспользуемый набор AI-агентов и скиллов для Claude Code и Codex: профили под стек, агенты, скиллы, хуки, пресеты; ставится плагинами или установщиком, есть адаптер для OpenCode.

## Подключить AIKit к проекту

### Плагинами — Claude Code и Codex

В Claude Code:

```text
/plugin marketplace add undef1ned-dev/ai-kit
/plugin install aikit@aikit
/plugin install vue-nuxt@aikit
/aikit:setup frontend-team
```

Ядро — плагин `aikit`, каждый профиль (`vue-nuxt`, `python-fastapi`, `python-django`) и пак (`quality`, `devops`, `ai`) — свой плагин. `/aikit:setup` записывает в проект блок правил в `CLAUDE.md`, контракты профилей в `.aikit/profiles.json`, память в `.aikit/memory/` и включённые плагины в `.claude/settings.json` — команда получит тот же набор.

В Codex: `codex plugin marketplace add undef1ned-dev/ai-kit`, `codex plugin add aikit@aikit` и плагины профилей, затем скилл `$setup`. Агентов плагины Codex не поставляют — `$setup` пишет их в `.codex/agents/`.

### Установщиком — OpenCode и запасной путь

```bash
git submodule add git@github.com:undef1ned-dev/ai-kit.git .aikit-config
git submodule update --init
bash .aikit-config/scripts/attach.sh --preset frontend-team
```

Вместо пресета можно указать профили и паки явно:

```bash
bash .aikit-config/scripts/attach.sh vue-nuxt --pack quality
bash .aikit-config/scripts/attach.sh vue-nuxt+python-fastapi
```

`attach.sh` создаёт `CLAUDE.md`, `.claude/agents/`, `.claude/skills/`, `.claude/settings.json`, `.mcp.json`, `PRODUCT.md`, контракты профилей в `.aikit/profiles.json` и память проекта в `.aikit/memory/`. Профили одного проекта могут жить в разных папках монорепо (`web/`, `api/`) — установщик найдёт их сам.

## Быстрый старт

1. Подключи пресет или профиль.
2. Заполни `PRODUCT.md` — агенты читают его как контекст продукта.
3. Запусти задачу: `/implement-feature <задача>` или `/workflow <задача>`, если не уверен, какая цепочка агентов нужна.

## Основные команды

- `/implement-feature` — реализация фичи через цепочку architect → coder → tester + reviewer; `--tdd` — сначала тесты, `--worktree` — в отдельном git worktree.
- `/fix-bug` — исправление бага: тест, который ловит баг, затем фикс.
- `/check-feature` — запуск приложения и проверка фичи в браузере.
- `/workflow` — визард: определяет тип задачи и строит цепочку агентов.
- `/design-implement` — реализация, где основной вход — дизайн.
- `/design-review` — проверка реализации на соответствие UI kit и макету.
- `/security-check` — аудит безопасности.
- `/capture-memory` — зафиксировать решения и паттерны после задачи.

Скиллы `git-commit` и `git-branch` применяются автоматически при коммитах и создании веток.

## Обновить подключённый кит

```bash
bash .aikit-config/scripts/update.sh
```

## Другие runtime: Codex, OpenCode

```bash
python3 .aikit-config/scripts/install-adapter-package.py codex --preset frontend-team --workspace <путь-к-проекту>
python3 .aikit-config/scripts/update-adapter-package.py codex --preset frontend-team --workspace <путь-к-проекту>
```

Вместо `codex` — `opencode`.

## Разрабатывать этот репозиторий

Для развития самого кита используй `/improve-aikit`. Агенты и скиллы кита в этот репозиторий не копируются — запускай Claude Code с плагином из рабочей копии:

```bash
claude --plugin-dir .
```

Все проверки CI локально: `bash scripts/ci/run-all.sh`. Подробно — [Разработка AIKit](docs/guide/developing-aikit.md).

## Документация

Сайт: **https://undef1ned-dev.github.io/ai-kit/** (или локально — [docs/site/index.html](docs/site/index.html)). Там простыми словами объяснено, что такое AIKit, есть словарь терминов, установка, каталог профилей, известные ошибки и roadmap, а также поиск по всему этому.

Тот же текст в Markdown лежит в [docs/guide/](docs/guide/index.md). Его правят люди и AI-агенты, а сайт собирается из него командой `python3 scripts/generate-docs.py`.

- [Что такое AIKit](docs/guide/index.md) и [термины](docs/guide/glossary.md)
- [Установка и первая задача](docs/guide/getting-started.md)
- [Как это работает](docs/guide/how-it-works.md)
- [Известные ошибки](docs/guide/known-issues.md)
- [Как добавить стек](docs/guide/adding-a-stack.md)
- [Разработка AIKit](docs/guide/developing-aikit.md) — устройство репозитория, правила и проверки
- [Roadmap](docs/roadmap.md) и [поддержка runtime](docs/runtime-support.md)
