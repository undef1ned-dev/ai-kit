---
name: "improve-aikit"
description: Развивать сам репозиторий AIKit через специализированного maintainer-агента. Подходит для добавления новых возможностей, улучшения routing, manifests, memory, docs и внутренних workflow с обязательной валидацией и обновлением memory.
version: "1.0.0"
profile: "base"
tags: ["meta", "repository", "tooling"]
orchestrates: ["aikit-maintainer"]
example_prompt: "/improve-aikit добавить нового агента для работы с локализацией"
---

Запусти агент `aikit-maintainer` для развития самого репозитория AIKit.

$ARGUMENTS

Агент обязан:
1. Собрать контекст из ключевых файлов репозитория и `.claude/memory/`
2. Определить тип изменения и минимальный scope
3. Реализовать изменение без нарушения manifests, frontmatter и текущего branding
4. Прогнать обязательную матрицу проверок
5. Обновить memory самого AIKit после успешной валидации
6. Вернуть структурированный `AIKIT_MAINTENANCE_REPORT`
