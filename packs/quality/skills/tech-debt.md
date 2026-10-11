---
name: "tech-debt"
description: Аудит технического долга в проекте. Выявляет God Objects, дублирование кода, нарушения архитектурных слоёв, незакрытые TODO. Формирует приоритизированный backlog улучшений.
version: "1.0.0"
profile: "pack:quality"
tags: ["quality", "tech-debt", "refactoring"]
orchestrates: ["quality-analyst"]
example_prompt: "/tech-debt"
---

Запусти агент `quality-analyst` для анализа технического долга.

$ARGUMENTS

Агент должен:
1. Найти God Objects (функции/классы >50/200 строк)
2. Найти дублирующийся код
3. Проверить соблюдение архитектурных слоёв
4. Найти TODO/FIXME/HACK комментарии
5. Сформировать приоритизированный P1/P2/P3 список с конкретными рекомендациями
