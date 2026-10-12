---
name: "audit-prompts"
description: "Аудит промптов LLM в проекте: неявный формат ответа, необработанные edge cases, противоречия, избыточность. Используй, когда пользователь просит проверить промпты или LLM-интеграцию."
version: "1.0.0"
profile: "pack:ai"
tags: ["ai", "llm", "prompts", "audit"]
orchestrates: ["prompt-engineer"]
example_prompt: "/audit-prompts"
---

Запусти агент `prompt-engineer` для аудита промптов в проекте.

$ARGUMENTS

Агент должен:
1. Найти все промпты в коде (grep по SystemMessage, system_prompt, SYSTEM и т.д.)
2. Проверить каждый по чеклисту качества
3. Выявить проблемные места (нечёткий формат, нет обработки edge cases)
4. Предложить конкретные улучшения с до/после примерами
