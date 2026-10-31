## Работа в Antigravity

- Правила проекта — `AGENTS.md`. Скиллы вызывай через `/name` или по описанию; задачу и флаги бери из сообщения пользователя.
- При установке плагинами скиллы, агенты, хуки и MCP загружаются из `~/.gemini/config/plugins/` (ядро `aikit`, выбранные профили и паки); при установке адаптером скиллы находятся в `.agents/skills/`, агенты — в `.agents/agents/`.
- Агенты вызываются через инструмент `invoke_subagent`: передавай имя роли из `.aikit/profiles.json` без префикса плагина в `TypeName`, краткое описание роли в `Role` и задачу с контекстом в `Prompt`. Локальный агент `aikit-maintainer` также вызывается без префикса.
- Независимых тестировщика и ревьюера запускай параллельно до ожидания завершения, а для продолжения работы уже запущенного сабагента используй `send_message`.
- Модели агентов: уровни `opus`, `sonnet`, `haiku` сопоставляются с моделями Antigravity (`pro`, `flash`) через `adapters/models.json`. Переопределения проекта хранятся в поле `antigravity` в `.aikit/models.json`: при вызове `invoke_subagent` передавай выбранный уровень в `Model` (`pro`, `flash`, `flash_lite`, `inherit`), а для локальных агентов в `.agents/agents/` применяй настройки через `scripts/agent_models.py apply --runtime antigravity`.
- Для установки и обновления плагинов в `~/.gemini/config/plugins/` используй `scripts/install-antigravity-plugins.py` (или скилл `/update-agents`). После первой установки плагинов перезапусти сессию Antigravity.
- Хуки (`hooks.json` в плагине `aikit` или `.agents/hooks.json` при установке адаптером) проверяй по отметкам `aikit_hook.py --status`.
- Контракты профилей — `.aikit/profiles.json`, командная память — `.aikit/memory/`. Для уточнений у пользователя используй инструмент `ask_question` или чат.
