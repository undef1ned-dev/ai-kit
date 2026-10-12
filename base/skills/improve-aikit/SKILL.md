---
name: "improve-aikit"
description: "Развивать сам репозиторий AIKit через агента aikit-maintainer: агенты, скиллы, манифесты, routing, память, документация. Запускай только по явной просьбе пользователя."
disable-model-invocation: true
version: "1.0.0"
profile: "base"
tags: ["meta", "repository", "tooling"]
orchestrates: ["aikit-maintainer"]
example_prompt: "/improve-aikit добавить нового агента для работы с локализацией"
---

Запусти агент `aikit-maintainer` для развития самого репозитория AIKit.

$ARGUMENTS

Агент обязан:
1. Собрать контекст из ключевых файлов репозитория и `.aikit/memory/`
2. Определить тип изменения и минимальный scope
3. Реализовать изменение без нарушения manifests, frontmatter и текущего branding
4. Прогнать обязательную матрицу проверок
5. Обновить memory самого AIKit после успешной валидации
6. Вернуть структурированный `AIKIT_MAINTENANCE_REPORT`
