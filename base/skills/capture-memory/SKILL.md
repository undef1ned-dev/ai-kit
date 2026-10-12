---
name: "capture-memory"
description: "Зафиксировать командную память после задачи: решения, паттерны и коррекции агентов в .aikit/memory/ (агент memory-writer). Запускай только по явной просьбе пользователя."
disable-model-invocation: true
version: "2.0.0"
profile: "base"
tags: ["memory", "documentation", "knowledge"]
orchestrates: ["memory-writer"]
example_prompt: "/capture-memory после рефакторинга network слоя"
---

Запусти агент `memory-writer`.

Он соберёт из задачи то, что пригодится команде: решения, паттерны, коррекции агентов. Отсеет личное и историю задачи, запишет в `.aikit/memory/` и спросит, как сохранить: оставить в рабочей папке, отдельным коммитом или отдельным PR.

$ARGUMENTS
