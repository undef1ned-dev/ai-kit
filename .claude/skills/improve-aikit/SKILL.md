---
name: improve-aikit
description: "Развить сам репозиторий AIKit по процессу сопровождающего aikit-maintainer: агенты, скиллы, профили, установщики, плагины, AIKit Deck, документация — с проверками run-all.sh. Только по явной команде разработчика кита."
disable-model-invocation: true
argument-hint: "<что изменить в ките>"
---

Запусти агента `aikit-maintainer` (`.claude/agents/aikit-maintainer.md`) с задачей пользователя.

Задача: $ARGUMENTS

Задачи нет — спроси, что изменить в ките.

Агент работает по своему процессу: контекст из `docs/guide/developing-aikit.md` → план → правка → `scripts/ci/run-all.sh` → документация → отчёт `AIKIT_MAINTENANCE_REPORT`. Перескажи пользователю отчёт коротко: что изменено, что проверено, что осталось. Коммит — только если пользователь попросит.
