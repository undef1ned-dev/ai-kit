---
name: "capture-memory"
description: "Зафиксировать контекст после завершённой задачи: решения, паттерны и коррекции агентов в .aikit/memory/ (агент memory-writer). Запускай только по явной просьбе пользователя."
disable-model-invocation: true
version: "1.0.0"
profile: "base"
tags: ["memory", "documentation", "knowledge"]
orchestrates: ["memory-writer"]
example_prompt: "/capture-memory после рефакторинга network слоя"
---

Запусти агент `memory-writer`.

Он соберёт контекст о выполненной задаче, определит scope (глобальный или по модулю),
создаст/обновит файлы в `.aikit/memory/`, синхронизирует `.claude/memory/`, создаст ветку и откроет MR на ревью.

$ARGUMENTS
