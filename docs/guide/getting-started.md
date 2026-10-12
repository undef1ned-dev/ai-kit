# Установка и первая задача

Как подключить AIKit к проекту, что появится в репозитории и как запустить первую задачу. На всё уходит минут десять.

## Что нужно

| Что | Зачем | Примечание |
|---|---|---|
| Git | Кит подключается как git submodule | — |
| Bash | Установщик `attach.sh` — bash-скрипт | На Windows — Git Bash (ставится вместе с Git for Windows) |
| Python 3.9+ | Установщики собирают контракты и MCP-конфиги, на нём работают хуки | Команда `python3`; на Windows см. [Известные ошибки](known-issues.md#windows-нет-команды-python3) |
| Runtime | Claude Code, Codex или OpenCode | Подойдёт любой из трёх, можно несколько сразу |
| `jq` | Склейка `settings.json` | Необязательно: без него сработает запасной путь на Python |

## Установка в Claude Code

<!-- steps -->
1. **Подключи кит к репозиторию проекта.** Из корня проекта:

   ```bash
   git submodule add git@github.com:undef1ned-dev/ai-kit.git .aikit-config
   git submodule update --init
   ```

2. **Выбери, что ставить.** Проще всего взять пресет — готовую комбинацию профилей и паков:

   | Пресет | Профили | Паки | Для кого |
   |---|---|---|---|
   | `frontend-team` | `vue-nuxt` | quality, devops | Фронтенд на Vue/Nuxt |
   | `backend-api` | `python-fastapi` | quality, devops, ai | API на FastAPI |
   | `backend-django` | `python-django` | quality, devops, ai | Бэкенд на Django |
   | `fullstack-web` | `vue-nuxt` + `python-fastapi` | quality, devops, ai | Nuxt-фронтенд и FastAPI-бэкенд в одном репозитории |

   Или собери набор сам — профили через `+`, паки флагом `--pack`.

3. **Запусти установщик:**

   ```bash
   bash .aikit-config/scripts/attach.sh --preset frontend-team
   ```

   Набор вручную:

   ```bash
   bash .aikit-config/scripts/attach.sh vue-nuxt --pack quality
   bash .aikit-config/scripts/attach.sh vue-nuxt+python-fastapi --pack quality --pack devops
   ```

4. **Заполни `PRODUCT.md`** в корне проекта: что за продукт, для кого, ключевые сущности. Агенты читают его перед решениями. Пустой шаблон тоже работает, но хуже.

5. **Закоммить результат.** Установка — обычные файлы в репозитории. Их коммитят, чтобы у всей команды был один и тот же набор.

## Что появится в проекте

| Файл или папка | Что это | В git |
|---|---|---|
| `CLAUDE.md` | [Правила проекта](glossary.md#правила-проекта): базовые плюс правила профилей | да |
| `.claude/agents/` | Агенты ядра, профилей и паков | да |
| `.claude/skills/` | Скиллы: `/name` или автовызов по описанию | да |
| `.claude/settings.json` | Разрешения на команды профиля, запрет чтения `.env`, без соавторства в коммитах, подключение хуков | да |
| `.aikit/hooks/aikit_hook.py` | [Хуки](how-it-works.md#хуки-правила-которые-соблюдаются-всегда): правила коммитов, веток и секретов, линтер после правки, тесты в конце ответа | да |
| `.mcp.json` | MCP-серверы | да |
| `.aikit/profiles.json` | Контракты профилей: агенты по ролям, папка `root`, команды проверки | да |
| `.aikit/profiles.kit-defaults.json` | Прежние значения кита — по ним обновление сохраняет твои правки | да |
| `.aikit/memory/` | [Память проекта](glossary.md#память-проекта) | да |
| `.claude/memory/` | Копия памяти для совместимости | да |
| `PRODUCT.md` | Описание продукта — заполняет команда | да |
| `.claude/.config-version` | Что и какой версии установлено — для `update.sh` | да |

> [!NOTE]
> В монорепо установщик сам найдёт папку каждого профиля по маркерам: `web/nuxt.config.ts` → профиль `vue-nuxt` живёт в `web/`. Найденная папка записывается в `root` в `.aikit/profiles.json`. Если угадал неверно — поправь `root` вручную, обновление правку сохранит.

## Первая задача

Открой runtime в корне проекта (`claude` в терминале или проект в приложении) и дай задачу:

```text
/implement-feature страница профиля пользователя: аватар, имя, email, кнопка «Выйти»
```

Ассистент выберет профиль, проведёт задачу через архитектора, кодера, тестировщика и ревьюера, запустит линтер и тесты и покажет итог. Если агенту что-то неясно, он остановится и спросит — отвечай на вопросы, это нормально.

Не уверен, какая цепочка нужна? Запусти визард — он сам определит тип задачи и покажет план до начала работы:

```text
/workflow хочу добавить экспорт отчётов в PDF
```

Как формулировать задачи, чтобы результат был лучше, — на странице [Работа с агентами](daily-work.md).

## Установка в Codex и OpenCode

Кит подключается так же, submodule в `.aikit-config`, а ставит его установщик адаптера:

```bash
python3 .aikit-config/scripts/install-adapter-package.py codex --preset frontend-team --workspace .
```

Вместо `codex` — `opencode`. Вместо `--preset` можно указать `--profile vue-nuxt+python-fastapi` и `--pack quality`.

Что появится: блок AIKit в `AGENTS.md` (твой текст вне блока сохраняется), скиллы в `.agents/skills/`, агенты в `.codex/agents/` или `.opencode/agents/`, MCP-серверы в `.codex/config.toml` или `opencode.json`, хуки в `.codex/hooks.json` или плагином `.opencode/plugins/aikit-hooks.js`, те же `.aikit/profiles.json`, `.aikit/hooks/` и `.aikit/memory/`.

> [!IMPORTANT]
> Codex применяет агентов, MCP и хуки из `.codex/` только в **доверенном** проекте. Отметь проект доверенным при первом запуске Codex — иначе агенты AIKit не загрузятся. Хуки Codex запускает только после одобрения: открой `/hooks` и отметь хуки AIKit доверенными; после обновления кита, если хуки изменились, — ещё раз. Figma и Sentry в Codex авторизуются командой `codex mcp login <name>`.

Скиллы в Codex вызываются через `$name` (например, `$implement-feature`), список — `/skills`. Остальные отличия runtime собраны на странице [Поддержка runtime](../runtime-support.md).

## Обновление

Claude Code:

```bash
bash .aikit-config/scripts/update.sh          # с вопросами
bash .aikit-config/scripts/update.sh --auto   # без вопросов
```

Codex и OpenCode:

```bash
python3 .aikit-config/scripts/update-adapter-package.py codex --preset frontend-team --workspace .
```

Что происходит при обновлении:

- кит подтягивает свежую версию — только если подключён как submodule и в нём нет локальных правок;
- агенты и скиллы кита перезаписываются — свои правки в них не делай, они потеряются;
- **`CLAUDE.md`** — `update.sh` покажет разницу и спросит, обновлять ли. При согласии старый файл сохранится в `CLAUDE.md.backup-<дата>`. В `--auto` файл обновляется без вопроса;
- **`.aikit/profiles.json`** — команды и `root`, которые поменяла команда, сохраняются; не тронутые — обновляются до новых значений кита;
- MCP-серверы и хуки, которые ты добавил сам, сохраняются; хуки AIKit обновляются.

Чтобы сменить пресет или набор профилей, запусти установщик заново с новым набором. В Codex и OpenCode файлы прошлой установки убираются. `attach.sh` убирает только скиллы, а агенты прежнего профиля остаются в `.claude/agents/` — удали их вручную (см. [Известные ошибки](known-issues.md#смена-профиля-оставляет-старых-агентов)).

## Проект, где кит уже подключён

Если ты клонируешь репозиторий, где AIKit уже стоит, подтяни submodule — остальное уже в git:

```bash
git clone <url-проекта>
cd <проект>
git submodule update --init
```
