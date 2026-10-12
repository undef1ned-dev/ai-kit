---
name: "optimize-memory"
description: "Консолидировать память проекта: архивировать старые задачи, сжать INDEX до 60 строк, объединить дублирующиеся паттерны. Обычно нужен после предупреждения от memory-status. Запускай только по явной просьбе пользователя."
disable-model-invocation: true
version: "1.0.0"
profile: "base"
tags: ["memory", "maintenance", "knowledge"]
orchestrates: ["memory-optimizer"]
example_prompt: "/optimize-memory архивируй старые задачи за прошлый квартал"
---

Запусти агент `memory-optimizer`.

$ARGUMENTS
