# AIKit

AIKit — переиспользуемый набор AI-агентов и скиллов для Claude Code: профили под стек, агенты, скиллы, пресеты и адаптеры для других runtime.

## Подключить AIKit к проекту

Из проекта, к которому нужно подключить AIKit:

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

- `/implement-feature` — реализация фичи через цепочку architect → coder → tester → reviewer.
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

Для развития самого кита используй `/improve-aikit`. Проверить установку можно на пустом проекте:

```bash
bash <путь-к-киту>/scripts/attach.sh --preset frontend-team
```

## Документация

- [docs-site/index.mdx](docs-site/index.mdx) — исходники сайта документации.
- `docs/generated/catalog.html` — каталог агентов и скиллов, собирается `python3 scripts/generate-catalog.py`.
- [docs/adding-a-stack.md](docs/adding-a-stack.md) — как добавить свой стек: контракт профиля и шаблон `scripts/new-profile.py`.
- [docs/roadmap.md](docs/roadmap.md) — план развития кита.
- [docs/runtime-support.md](docs/runtime-support.md) — что работает в Claude Code, Codex и OpenCode.
- [docs/research/](docs/research/) — исследования и планы модернизации.
