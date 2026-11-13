# Установка и обновление

Как подключить и обновлять AIKit в проекте для Claude Code, Codex и Antigravity.

## Установка

### Какой пресет выбрать для Nuxt

| Проект | Пресет | Состав |
|---|---|---|
| Nuxt 3 или 4 с внешним API (например, Django) или без собственного API | `frontend-team` | `vue-nuxt` + `devops` |
| Nuxt 3 или 4 с собственным Nitro API, Prisma и PostgreSQL | `nuxt-fullstack` | `vue-nuxt` + `nuxt-postgres` + `devops` |

Для `nuxt-fullstack` установи также плагин `nuxt-postgres@aikit` и передай имя пресета в `setup`. Пресет подключает инструкции и скиллы AIKit к существующему приложению. Зависимости, база и миграции настраиваются командами проекта. Если проект использует Bun, pnpm или свои скрипты, укажи команды в `.aikit/profiles.json`. AIKit сохраняет их при обновлении.

Профиль `vue-nuxt` учитывает фактический `srcDir` и серверный каталог проекта. При внешнем API он использует уже выбранный способ интеграции. [Структура каталогов Nuxt](https://nuxt.com/docs/4.x/getting-started/upgrade#new-directory-structure)

### Claude Code

Каждый профиль и пак — отдельный плагин маркетплейса `aikit`, ядро — плагин `aikit`.

<!-- steps -->
1. **Добавь маркетплейс и поставь плагины один раз на машину**:

   ```text
   claude plugin marketplace add undef1ned-dev/ai-kit
   claude plugin install aikit@aikit --scope user
   claude plugin install vue-nuxt@aikit --scope user
   claude plugin install devops@aikit --scope user
   ```

   Ставь плагины профилей и паков своего набора (например, пресет `frontend-team` включает профиль `vue-nuxt` и пак `devops`).

2. **Подключи проект** — в корне проекта:

   ```text
   /aikit:setup frontend-team
   ```

   Аргумент — пресет или профили через `+`. Без аргумента скилл определит стек по проекту и предложит выбор, а также спросит режим оформления коммитов (`ask` или `auto`, [подробнее](commands.md#коммиты-с-вопросом-или-без)).

3. **Выключи глобальное включение AIKit.** После подключения нужных репозиториев выполни `claude plugin disable <плагин>@aikit --scope user` для каждого плагина AIKit. Общая установка остаётся, а включение в `.claude/settings.json` имеет приоритет. Для следующего проекта вызови установщик из установленного ядра через `python3 "<корень плагина>/scripts/plugin-init.py" --runtime claude --preset frontend-team`. Путь к ядру указан как `installPath` в `claude plugin list --json`. [Области установки Claude Code](https://code.claude.com/docs/en/discover-plugins#choose-an-install-scope)

4. **Заполни `PRODUCT.md` и закоммить результат.** В `PRODUCT.md` опиши продукт, стек и бизнес-правила. В `.claude/settings.json` записаны маркетплейс и включённые плагины. На новой машине каждый участник один раз устанавливает этот набор.

Скиллы плагинов вызываются как `/name` или с префиксом плагина (`/aikit:implement-feature`, `/vue-nuxt:new-page`). Сбоку открывается [панель AIKit Deck](commands.md#панель-aikit-deck) (повторное открытие — `/deck`).

### Codex

<!-- steps -->
1. **Добавь маркетплейс и установи плагины в общий кэш Codex один раз на машину.** Для `frontend-team`:

   ```bash
   codex plugin marketplace add undef1ned-dev/ai-kit
   codex plugin add aikit@aikit
   codex plugin add vue-nuxt@aikit
   codex plugin add devops@aikit
   ```

2. **Подключи проект** — в корне проекта вызови скилл `$aikit:setup` с пресетом или профилями:

   ```text
   $aikit:setup frontend-team
   ```

   Setup включает ядро и выбранные профили и паки в проектном `.codex/config.toml`, записывает агентов в `.codex/agents/`, правила в `AGENTS.md` и скрипт обновления в `.aikit/scripts/update-agents.sh`.

   Если AIKit уже выключен глобально, для следующего проекта сразу запусти тот же установщик из корня нового проекта. Подставь версию установленного ядра из `codex plugin list --marketplace aikit`:

   ```bash
   python3 "${CODEX_HOME:-$HOME/.codex}/plugins/cache/aikit/aikit/<версия>/scripts/plugin-init.py" --runtime codex --preset frontend-team
   ```

3. **Выключи глобальное включение AIKit.** `codex plugin add` включает плагин в пользовательском конфиге. Сначала подключи новые проекты через `setup` и обнови ранее подключённые через [`$aikit:update`](#файлы-подключённого-проекта). Затем выставь `enabled = false` в каждой секции `[plugins."…@aikit"]` пользовательского `~/.codex/config.toml` (или `$CODEX_HOME/config.toml`). Кэш и маркетплейс остаются общими. В новой сессии доверенный проект применит своё `enabled = true`. [Настройки плагинов в Codex](https://developers.openai.com/plugins/build/plugins#enable-or-disable-a-plugin-for-a-repo)

4. **Заполни `PRODUCT.md` и закоммить результат**, включая проектный `.codex/config.toml`.

> [!IMPORTANT]
> Codex требует Python 3.11+ и применяет агентов, MCP и хуки из `.codex/` только в **доверенном** проекте. Отметь проект доверенным при первом запуске и одобри хуки в `/hooks`. Figma и Sentry в Codex авторизуются командой `codex mcp login <name>`. Проверить готовность конфигурации без изменения файлов можно командой `$aikit:setup --check`.

### Antigravity

<!-- steps -->
1. **Собери и установи плагины AIKit** в глобальный каталог Antigravity (`~/.gemini/config/plugins/`):

   ```bash
   python3 scripts/install-antigravity-plugins.py --preset frontend-team
   # или все плагины репозитория
   python3 scripts/install-antigravity-plugins.py --all
   ```

2. **Подключи проект** — перезапусти сессию Antigravity и в корне проекта вызови скилл `/setup`:

   ```text
   /setup frontend-team
   ```

   Или запусти скрипт напрямую:

   ```bash
   python3 ~/.gemini/config/plugins/aikit/scripts/plugin-init.py --runtime antigravity --preset frontend-team --workspace .
   ```

   Скрипт запишет блок правил в `AGENTS.md`, контракты в `.aikit/profiles.json`, память, агентов проекта в `.agents/agents/` и скрипт обновления в `.aikit/scripts/update-agents.sh`.

3. **Заполни `PRODUCT.md` и закоммить результат.**

## Обновление

Когда в `main` выходит новая версия, при старте сессии AIKit сообщает: «AIKit: доступна версия X.Y.Z (у вас A.B.C)» — подробнее в [Известных ошибках](known-issues.md#уведомление-о-новой-версии-aikit). Чтобы сменить набор профилей или паков, запусти `setup` заново — правки команды в `.aikit/profiles.json` и текст вне блока AIKit в `CLAUDE.md` / `AGENTS.md` сохранятся.

### Файлы подключённого проекта

Обнови общие плагины один раз по инструкции для своего runtime ниже и открой новую сессию. В корне уже подключённого проекта запусти `$aikit:update` в Codex, `/aikit:update` в Claude Code или `/update` в Antigravity. Флаг `--dry-run` покажет версии и план без записи. Для запуска из терминала используй тот же установщик, который вызывается из setup:

```bash
python3 "<корень установленного плагина>/scripts/plugin-init.py" --runtime codex --update --workspace .
```

В Claude Code передай `--runtime claude`, в Antigravity — `--runtime antigravity`. Команда берёт профили и паки из `.aikit/plugin-init.json` и применяет только подходящие записи журнала. Она показывает изменённые файлы и записывает новую версию проекта отдельно для каждого runtime. Сохраняются настройки команды, память, свои агенты, текст вне блока AIKit и переопределённые команды, действия и корни профилей. Если в старой установке версия проектных файлов отсутствует, при первом запуске применяются все подходящие записи, включая проектное включение плагинов Codex.

Codex и Antigravity используют общий `AGENTS.md`. Если подключены оба runtime, блок правил обновляется из runtime, для которого этот блок был установлен.

### Claude Code

Обнови каталог маркетплейса и установленные плагины:

```bash
claude plugin marketplace update aikit
claude plugin update aikit@aikit --scope user
claude plugin update vue-nuxt@aikit --scope user
claude plugin update devops@aikit --scope user
```

Также обновить кит и профили можно кнопками «Обновить кит» и «Обновить профиль» в панели [AIKit Deck](commands.md#панель-aikit-deck). Изменения подхватываются после перезапуска сессии.

### Codex

Во время `setup` в проект устанавливается кроссплатформенный скрипт `.aikit/scripts/update-agents.sh` (работает на Linux, macOS и в Git Bash на Windows). Он сам определяет подключённые в проекте runtime (если подключены и Codex, и Antigravity — обновит оба) и выполняет полное обновление:

```bash
bash .aikit/scripts/update-agents.sh
```

Или вызови скилл внутри сессии Codex:

```text
$aikit:update-agents --with-plugins
```

Нужен Python 3.11+. Обновляется маркетплейс `aikit` (все установленные из него плагины), проверяются версии ядра и выбранных профилей и паков, а затем пересобираются агенты в `.codex/agents/` из свежего источника.

**Нюансы обновления в Codex:**

- **Общий кэш и агенты проектов:** `codex plugin marketplace upgrade aikit` обновляет установленные плагины в общем кэше одной командой. Агенты лежат в каждом проекте. После общего обновления при необходимости пересобери их в нужном проекте.
- **Если плагины уже обновлены вручную:** запусти `bash .aikit/scripts/update-agents.sh --agents-only` (или скилл `$aikit:update-agents` без флага `--with-plugins`) — это только пересоберёт агентов в `.codex/agents/`. Чтобы обновить только Codex в проекте с несколькими runtime, передай аргумент `codex`: `bash .aikit/scripts/update-agents.sh codex`.
- **Файлы проекта:** `update-agents` пересобирает агентов. Для миграций правил, контрактов и конфигурации запускай `$aikit:update`. Для смены профилей используй `$aikit:setup`.
- **После обновления:** открой новую сессию Codex, а если изменились хуки — одобри их повторно в `/hooks`.

### Antigravity

Запусти из корня проекта скрипт обновления, который появился во время `setup` (работает на Linux, macOS и в Git Bash на Windows):

```bash
bash .aikit/scripts/update-agents.sh
```

Скрипт сам определит, что проект подключён к Antigravity, скачает свежие плагины в `~/.gemini/config/plugins/` и пересоберёт агентов проекта в `.agents/agents/`.

- **Только пересобрать агентов** (если глобальные плагины уже обновлены): `bash .aikit/scripts/update-agents.sh --agents-only` или скилл `/update-agents` в чате.
- **Обновить только Antigravity** (если в проекте несколько runtime): `bash .aikit/scripts/update-agents.sh antigravity`.
- Для обновления правил, контрактов и других проектных файлов открой новую сессию и запусти `/update`. Скрипт `update-agents.sh` обновляет плагины и агентов.
