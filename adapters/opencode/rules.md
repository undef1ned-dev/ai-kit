## Работа в OpenCode

- Правила проекта — `AGENTS.md`. Используй скиллы по имени или описанию; задачу бери из сообщения пользователя.
- Скиллы AIKit — `.agents/skills/`, агенты — `.opencode/agents/*.md`. Имена агентов из `.aikit/profiles.json` используй без префикса плагина.
- Модели агентов задаются как `provider/model` в определении агента. Переопределения проекта — поле `opencode` в `.aikit/models.json`; применяй их через `scripts/agent_models.py apply --runtime opencode` из кита или его копии в `.aikit/`.
- MCP и разрешения — `opencode.json`, хуки — `.opencode/plugins/`. Не считай текстовое правило технической блокировкой инструмента.
- Контракты профилей — `.aikit/profiles.json`, командная память — `.aikit/memory/`. Возможности, недоступные в OpenCode, сообщай явно.
