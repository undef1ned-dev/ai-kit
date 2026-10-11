---
name: "memory-status"
description: Показать текущее состояние canonical памяти проекта и Claude mirror — что накоплено, последние задачи, открытые MR с memory-изменениями.
version: "1.0.0"
profile: "base"
tags: ["memory", "status", "knowledge"]
orchestrates: []
example_prompt: "/memory-status"
---

Выполни следующие шаги:

## 1. Прочитай память

```bash
# Размер INDEX
wc -l .aikit/memory/INDEX.md 2>/dev/null || echo "Memory не инициализирована"

# Количество активных задач
ls .aikit/memory/tasks/*.md 2>/dev/null | grep -v archive | wc -l || echo 0

# Количество архивных задач
ls .aikit/memory/tasks/archive/*.md 2>/dev/null | wc -l || echo 0

# Количество решений
ls .aikit/memory/decisions/*.md 2>/dev/null | grep -v gitkeep | wc -l || echo 0

# Количество паттернов
ls .aikit/memory/patterns/*.md 2>/dev/null | grep -v gitkeep | wc -l || echo 0

# Количество коррекций
ls .aikit/memory/corrections/*.md 2>/dev/null | grep -v gitkeep | wc -l || echo 0

# Feature-модули
ls -d .aikit/memory/features/*/ 2>/dev/null || echo "нет"
```

Если `.aikit/memory/INDEX.md` существует — прочитай его.

## 2. Проверь открытые MR

Через GitLab MCP найди открытые MR с memory-изменениями:
```
mcp__gitlab__list_merge_requests с фильтром: labels=["memory"], state=opened
```

Если GitLab MCP недоступен — пропусти этот шаг.

## 3. Выведи отчёт

```
📚 Project Memory Status

INDEX:        {N} строк из 60 максимальных  {⚠️ если > 50}
Задачи:       {N} активных  {+ N архивных если есть}
Решений:      {N}
Паттернов:    {N}
Коррекций:    {N}
Feature-модули: {список модулей или "нет"}

Mirror:
canonical `.aikit/memory/` → {ok | missing}
claude `.claude/memory/` → {ok | missing}

Последние задачи:
{5 последних из INDEX или "нет задач"}

Открытые memory-MR:
{список или "нет открытых MR"}

{если INDEX > 50: ⚠️  Рекомендуется запустить /optimize-memory}
{если memory не инициализирована: ℹ️  Память не инициализирована. Запусти /capture-memory после первой задачи.}
```

$ARGUMENTS
