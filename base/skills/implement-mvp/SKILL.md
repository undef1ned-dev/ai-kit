---
name: "implement-mvp"
description: "Перевести MVP-документ из docs/mvp/ в технический план: API-контракт, scope по платформам, порядок реализации (агент tech-planner). Используй после analyze-mvp, когда идея одобрена и нужно спланировать разработку."
version: "1.0.0"
profile: "base"
tags: ["planning", "architecture", "cross-platform"]
orchestrates: ["tech-planner"]
example_prompt: "/implement-mvp docs/mvp/referral-system.md"
---

Запусти агент `tech-planner` для следующего MVP или пути к документу:

$ARGUMENTS

Если аргумент не передан — найди последний документ в `docs/mvp/` и уточни у разработчика с каким работаем.

Агент должен:
1. Прочитать MVP-документ из `docs/mvp/`
2. Прочитать `PRODUCT.md` и `CLAUDE.md` для контекста стека
3. Определить какие профили проекта задействованы (`.aikit/profiles.json`: `role` — `backend`, `web`, …)
4. Спроектировать API-контракт если задействован Backend
5. Описать технический scope для каждой платформы
6. Определить порядок реализации и зависимости
7. Вывести блок `TECH_PLAN`

После получения `TECH_PLAN` запускай архитекторов задействованных профилей — `agents.architect` из `.aikit/profiles.json`:
- архитектор профиля с `role: backend` читает BACKEND SCOPE и API CONTRACT;
- архитектор профиля с `role: web` читает WEB SCOPE и API CONTRACT.

Рекомендуемый порядок: сначала backend-архитектор, чтобы зафиксировать API, затем web.
