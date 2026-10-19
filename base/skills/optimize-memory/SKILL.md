---
name: "optimize-memory"
description: "Консолидировать командную память .aikit/memory/: сжать INDEX до 60 строк, объединить дубли, убрать устаревшее, перенести решения из логов задач прежних версий. Обычно нужен после предупреждения от memory-status. Запускай только по явной просьбе пользователя."
argument-hint: "[что оптимизировать]"
disable-model-invocation: true
version: "2.0.0"
profile: "base"
tags: ["memory", "maintenance", "knowledge"]
orchestrates: ["memory-optimizer"]
example_prompt: "/optimize-memory объедини дублирующиеся паттерны"
---

Запусти агент `memory-optimizer`.

$ARGUMENTS
