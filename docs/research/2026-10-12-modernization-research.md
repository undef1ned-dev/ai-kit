# Ресерч: модернизация AIKit

> Дата: 2026-10-12
> Репозиторий: `undef1ned-dev/ai-kit`.
> Назначение: стартовый контекст для следующих сессий доработки кита.

---

## 1. Что это за проект

AIKit — переиспользуемый набор «AI-сотрудников» для Claude Code (плюс адаптеры для Codex, GLM, OpenCode), который подключается к проекту.

- **Профили** (`profiles/`) — правила и агенты под стек: `vue-nuxt`, `ios-swiftui`, `android-kotlin`, `python-fastapi`, `python-django`, `aikit-repo`.
- **Пресеты** (`presets/*.json`) — наборы профилей + паков под тип команды: `frontend-team`, `backend-api`, `backend-django`, `fullstack-web`, `mobile-ios`, `mobile-android` (часть помечена `deprecated`).
- **Паки** (`packs/`) — `ai`, `devops`, `quality`; у пака есть `compatible_profiles`.
- **Базовый слой** (`base/`) — общие агенты и скиллы: `analyze-mvp`, `implement-mvp`, `workflow`, `security-check`, `write-ui-texts`, `cross-check`, `create-agent`, `create-skill`, `improve-aikit`, `capture-memory`, `memory-status`, `optimize-memory`.
- **Память** (`.aikit/memory/`, зеркало `.claude/memory/`) — решения, паттерны, коррекции агентов, логи задач.

Типичная цепочка профиля: `/implement-feature` → architect → coder → tester → reviewer.

### Подключение (текущий способ)

```bash
git submodule add <repo-url> .aikit-config
git submodule update --init
bash .aikit-config/scripts/attach.sh --preset frontend-team   # или: attach.sh <profile>[+<profile2>] [--pack <pack>]
```

Затем `/aikit-bootstrap-project` и `/aikit-doctor --scope install`.
`attach.sh` требует профиль или пресет — без них не запускается.

---

## 2. Как устроен `/capture-memory`

Скилл `base/skills/capture-memory.md` только запускает агента `base/agents/memory-writer.md`:

1. Собирает контекст задачи из диалога (или задаёт до 4 вопросов).
2. Выбирает scope: `features/<module>/` (один модуль) или глобальный; коррекции агентов — всегда `corrections/<agent>.md`.
3. Пишет `tasks/YYYY-MM-DD-<slug>.md`, при необходимости `decisions/NNN-*.md`, `patterns/*.md`, `corrections/*.md`; обновляет `INDEX.md` (лимит 60 строк, 5 последних задач).
4. Синхронизирует зеркало: `python3 scripts/sync-memory-mirror.py --source canonical`.
5. Ищет ревьюера в `PRODUCT.md`, создаёт ветку `memory/<date>-<slug>`, коммит, **`git push`** и MR **через GitLab MCP** (репозиторий же на GitHub → фолбэк на ручную ссылку).

Агенты профилей читают `.claude/memory/INDEX.md` и свою коррекцию (например `profiles/vue-nuxt/agents/vue-architect.md:24`).

---

## 3. Что устарело / чего не хватает (находки)

| # | Наблюдение | Где |
|---|---|---|
| F1 | Команды ставятся как legacy slash-commands в `.claude/commands/`, а не как Skills (`.claude/skills/<name>/SKILL.md` с автовызовом по description и вложенными файлами) | `scripts/attach.sh:234`, `:308` |
| F2 | Нет ни одного хука — правила `CLAUDE.md` (без `any`, Conventional Commits, без секретов) держатся только на памяти модели | `.claude/`, `profiles/*/settings.json` |
| F3 | Дистрибуция только через git submodule + bash; нет Claude Code plugin / marketplace; на Windows нужен Git Bash | `scripts/attach.sh`, `scripts/update.sh` |
| F4 | MCP-серверы лежат в `settings.json` профиля, который `attach.sh` кладёт в `.gitignore`; командный стандарт — `.mcp.json`. Playwright MCP на `@latest` без пина, Figma — сторонний `figma-developer-mcp` вместо официального | `profiles/vue-nuxt/settings.json`, `scripts/attach.sh:403` |
| F5 | Проектная память пересекается со встроенной auto-memory Claude Code; memory-writer завязан на GitLab и сам пушит | `base/agents/memory-writer.md` |
| F6 | Нет eval-ов агентов — изменения промптов не измеряются | — |
| F7 | Кит сильно разросся: ~4400 файлов, 750+ коммитов фаз P1–P240; много внутренних контрактов/валидаторов, не влияющих на пользовательский путь | `.aikit/memory/decisions/`, `scripts/`, `schemas/` |
| F8 | Нет профиля под Java (например, Minecraft-моды) | `profiles/` |

---

## 4. План доработок (по приоритету)

### P1. Миграция на современный формат
1. **Skills вместо commands.** Перевести `base/skills/*.md` и `profiles/*/skills/*.md` в `SKILL.md`-формат; переписать `description` под автовызов; положить рядом шаблоны (например, шаблоны memory-writer).
2. **Plugin + marketplace.** Каждый профиль/пресет — плагин; установка `/plugin marketplace add undef1ned-dev/ai-kit` → `/plugin install <plugin>`. `attach.sh` оставить как fallback.
3. **`.mcp.json`** вместо `mcpServers` в `settings.json`; запинить версии; официальный Figma MCP.

> Перед реализацией сверить актуальный формат Skills / plugin.json / marketplace.json / hooks по документации Claude Code.

### P2. Хуки (детерминированное соблюдение правил)
4. **PostToolUse** на Edit/Write — линтер/форматтер профиля (`eslint --fix`/`prettier`, `ruff`, `ktlint`, `swiftformat`).
5. **PreToolUse** — блок записи секретов, `.env`, `git add .env`.
6. **Проверка Conventional Commits** перед `git commit`.
7. **Stop** — если менялся код: напомнить/запустить тесты; после крупной задачи предложить `/capture-memory`.
8. **SessionStart** — подгружать `INDEX.md` памяти и `PRODUCT.md` в контекст.

### P3. Агенты и workflow
9. `/implement-feature`: tester и reviewer параллельно в фоне; coder в изолированном git worktree.
10. Ревьюеры профилей опираются на встроенный `/code-review` + свои профильные проверки.
11. TDD-режим (`/tdd` или флаг): сначала падающие тесты, потом реализация.
12. `/fix-bug`: воспроизвести → тест на баг → фикс → проверка.
13. `/verify` (`/run`): запуск приложения и проверка в браузере через Playwright / встроенный браузер.

### P4. Качество агентов
14. Eval-набор через `claude plugin eval`: эталонные задачи на каждый профиль, прогон в CI на PR, меняющих агентов.

### P5. Автоматизация вне сессии
15. Регулярные `/security-check`, `/tech-debt` через `/schedule`.
16. PR-ревью агентом профиля в GitHub Actions (`.github/workflows/` уже есть).

### P6. Память
17. Разграничить с встроенной памятью Claude Code: в `.aikit/memory/` — только командное (решения, коррекции агентов).
18. Поддержать GitHub (`gh pr create`), сделать push/PR опциональными.

### P7. Новые профили и UX
19. Профиль `java-minecraft` (см. §5) и при необходимости `react-next`, `go`.
20. Мод-панель «AIKit Deck» (см. §6).
21. Statusline: профиль, размер памяти, предупреждение «пора `/optimize-memory`».

### P8. Упрощение (отдельной задачей)
22. Аудит реально используемого; валидаторы/контракты фаз P1–P240 без пользовательской ценности — в архив.

**Рекомендованный старт:** P1 (пп. 1–2) + P2 (пп. 4–6), затем пп. 9 и 14.

---

## 5. Идея: профиль `java-minecraft`

Структура по образцу `profiles/android-kotlin/`:

```text
profiles/java-minecraft/
  CLAUDE.md                — правила стека
  profile.manifest.json
  workflow.manifest.json
  capabilities.json
  settings.json            — permissions (./gradlew …)
  agents/                  — architect, coder, tester, reviewer
  skills/                  — implement-feature, add-tests, new-block, new-item …
```

Перед созданием зафиксировать: загрузчик (Fabric / NeoForge / Forge), версии Minecraft и Java, команды (`./gradlew build`, `runClient`, `runGametest`), правила кода (регистрация через `ModBlocks`/`ModItems`, клиентский код отдельно, mixin — крайняя мера). Запуск: `/improve-aikit Добавить профиль java-minecraft …`. Пак `quality` подключать только если профиль добавлен в его `compatible_profiles`.

---

## 6. Идея: мод-панель «AIKit Deck» для Claude Code

Проверено по типам Claude Code (build 2.1.295) — всё нужное есть:

- панель: `$.ui.open({ id, title })` + хук `ui.render` на `{ component: 'Pane' }`;
- элементы desktop/terminal/vscode: `Box`, `Text`, `Button`, `Input`, `Select`, `Markdown` (на mobile нет `Input`/`Select`);
- запуск команды: `$.prompt.submit({ text })`; мягкий режим — `$.prompt.fill(...)` (вставить в поле ввода);
- автосписок команд: чтение `.claude/skills/` и `.claude/agents/` через `$.fs`.

Макет: группы кнопок (Разработка / Анализ и качество / Память), поле «Задача», переключатель «Вставить / Отправить», история последних запусков. Ограничение: интерактивные скиллы (`/create-agent`, `/analyze-mvp`, `/workflow`) всё равно продолжаются в чате. Мод можно поставлять вместе с плагином кита (P1.2).
