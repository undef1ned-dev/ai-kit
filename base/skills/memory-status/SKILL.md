---
name: "memory-status"
description: "Показать состояние командной памяти проекта (.aikit/memory/): что накоплено, размер INDEX, открытые memory-PR и нужна ли оптимизация. Используй, когда пользователь спрашивает, что записано в памяти проекта."
version: "2.0.0"
profile: "base"
tags: ["memory", "status", "knowledge"]
orchestrates: []
example_prompt: "/memory-status"
---

Выполни следующие шаги:

## 1. Прочитай память

```bash
wc -l .aikit/memory/INDEX.md 2>/dev/null || echo "Память не инициализирована"
ls .aikit/memory/decisions/*.md 2>/dev/null | wc -l
ls .aikit/memory/patterns/*.md 2>/dev/null | wc -l
ls .aikit/memory/corrections/*.md 2>/dev/null | wc -l
ls -d .aikit/memory/features/*/ 2>/dev/null || echo "нет"
find .aikit/memory/tasks -name "*.md" 2>/dev/null | wc -l
test -d .claude/memory && echo "есть .claude/memory/"
```

Если `.aikit/memory/INDEX.md` существует — прочитай его.

## 2. Открытые memory-PR

Определи хостинг по `git remote get-url origin`:
- GitHub и есть `gh` — `gh pr list --state open --search "docs(memory) in:title"`;
- GitLab и есть `glab` — `glab mr list --search "docs(memory)"`;
- иначе пропусти шаг и напиши об этом в отчёте.

## 3. Отчёт

```
📚 Командная память

INDEX:      {N} строк из 60  {⚠️ если > 50}
Решений:    {N}
Паттернов:  {N}
Коррекций:  {N}
Модули:     {список или "нет"}

Последние записи:
{3–5 последних строк из INDEX или "пока пусто"}

Открытые memory-PR:
{список | "нет" | "не проверено: нет gh / glab"}

{если INDEX > 50: ⚠️ Запусти /optimize-memory}
{если есть логи задач в tasks/: ℹ️ Это формат прежних версий — /optimize-memory перенесёт из них решения}
{если есть .claude/memory/: ℹ️ .claude/memory/ больше не используется — агенты читают .aikit/memory/. Папку можно удалить}
{если память не инициализирована: ℹ️ Запусти /capture-memory после первой задачи с решениями}
```

Личная память runtime (auto memory Claude Code и т. п.) в этот отчёт не входит: она у каждого разработчика своя.

$ARGUMENTS
