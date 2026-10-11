---
name: "optimize-memory"
description: Консолидировать память проекта — архивировать старые задачи, сжать INDEX до 60 строк, объединить дублирующиеся паттерны. Запускай когда /memory-status показывает предупреждение.
version: "1.0.0"
profile: "base"
tags: ["memory", "maintenance", "knowledge"]
orchestrates: ["memory-optimizer"]
example_prompt: "/optimize-memory архивируй старые задачи за прошлый квартал"
---

Запусти агент `memory-optimizer`.

$ARGUMENTS
