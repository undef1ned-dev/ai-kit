# Установка и обновление

Как подключить и обновлять AIKit в проекте для Claude Code, Codex и Antigravity.

## Установка

### Claude Code

Каждый профиль и пак — отдельный плагин маркетплейса `aikit`, ядро — плагин `aikit`.

<!-- steps -->
1. **Добавь маркетплейс и поставь плагины** — в Claude Code:

   ```text
   /plugin marketplace add undef1ned-dev/ai-kit
   /plugin install aikit@aikit
   /plugin install vue-nuxt@aikit
   /plugin install devops@aikit
   ```

   Ставь плагины профилей и паков своего набора (например, пресет `frontend-team` включает профиль `vue-nuxt` и пак `devops`).

2. **Подключи проект** — в корне проекта:

   ```text
   /aikit:setup frontend-team
   ```

   Аргумент — пресет или профили через `+`. Без аргумента скилл определит стек по проекту и предложит выбор, а также спросит режим оформления коммитов (`ask` или `auto`, [подробнее](commands.md#коммиты-с-вопросом-или-без)).

3. **Заполни `PRODUCT.md` и закоммить результат.** В `PRODUCT.md` опиши продукт, стек и бизнес-правила — агенты читают его перед решениями. В `.claude/settings.json` записаны маркетплейс и включённые плагины: участники команды получат их, когда откроют проект и доверят папку.

Скиллы плагинов вызываются как `/name` или с префиксом плагина (`/aikit:implement-feature`, `/vue-nuxt:new-page`). Сбоку открывается [панель AIKit Deck](commands.md#панель-aikit-deck) (повторное открытие — `/deck`).

### Codex

<!-- steps -->
1. **Добавь маркетплейс и плагины:**

   ```bash
   codex plugin marketplace add undef1ned-dev/ai-kit
   codex plugin add aikit@aikit
   codex plugin add vue-nuxt@aikit
   ```

2. **Подключи проект** — в корне проекта вызови скилл `$setup` с пресетом или профилями:

   ```text
   $aikit:setup frontend-team
   ```

   Плагины Codex не умеют поставлять агентов, поэтому скилл записывает их в `.codex/agents/`, правила проекта — блоком в `AGENTS.md`, а скрипт обновления — в `.aikit/scripts/update-agents.sh`.

3. **Заполни `PRODUCT.md` и закоммить результат.**

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

### Claude Code

Обнови каталог маркетплейса и установленные плагины:

```text
/plugin marketplace update aikit
/plugin update aikit@aikit
/plugin update vue-nuxt@aikit
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

- **Почему нужно обновлять агентов отдельно от плагинов:** сам Codex обновляет плагины при смене версии в маркетплейсе (`codex plugin marketplace upgrade aikit`), но плагины Codex не умеют поставлять агентов — файлы в `.codex/agents/` остаются прежними, пока их не пересоберёт скрипт или скилл.
- **Если плагины уже обновлены вручную:** запусти `bash .aikit/scripts/update-agents.sh --agents-only` (или скилл `$aikit:update-agents` без флага `--with-plugins`) — это только пересоберёт агентов в `.codex/agents/`. Чтобы обновить только Codex в проекте с несколькими runtime, передай аргумент `codex`: `bash .aikit/scripts/update-agents.sh codex`.
- **Что сохраняется:** правила в `AGENTS.md`, контракты `.aikit/profiles.json`, память, настройки команды и собственные агенты проекта не меняются (для обновления правил или смены профилей используй `$aikit:setup`).
- **После обновления:** открой новую сессию Codex, а если изменились хуки — одобри их повторно в `/hooks`.

### Antigravity

Запусти из корня проекта скрипт обновления, который появился во время `setup` (работает на Linux, macOS и в Git Bash на Windows):

```bash
bash .aikit/scripts/update-agents.sh
```

Скрипт сам определит, что проект подключён к Antigravity, скачает свежие плагины в `~/.gemini/config/plugins/` и пересоберёт агентов проекта в `.agents/agents/`.

- **Только пересобрать агентов** (если глобальные плагины уже обновлены): `bash .aikit/scripts/update-agents.sh --agents-only` или скилл `/update-agents` в чате.
- **Обновить только Antigravity** (если в проекте несколько runtime): `bash .aikit/scripts/update-agents.sh antigravity`.
- Правила в `AGENTS.md`, `.aikit/profiles.json`, память, настройки и собственные агенты команды сохраняются. Перезапусти сессию Antigravity, чтобы изменения вступили в силу.
