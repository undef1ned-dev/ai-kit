---
name: "capture-memory"
description: Зафиксировать контекст после завершённой задачи. Агент memory-writer создаст файлы в canonical .aikit/memory/, синхронизирует Claude mirror и откроет MR на ревью для всей команды.
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
