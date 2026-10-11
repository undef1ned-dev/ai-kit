---
name: "implement-mvp"
description: Запустить технический планировщик для MVP-документа. Агент читает продуктовый анализ из docs/mvp/ и формирует TECH_PLAN — технический план реализации с API-контрактом и scope по платформам. После этого можно запускать платформенных архитекторов.
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
3. Определить какие платформы задействованы (Backend / iOS / Android)
4. Спроектировать API-контракт если задействован Backend
5. Описать технический scope для каждой платформы
6. Определить порядок реализации и зависимости
7. Вывести блок `TECH_PLAN`

После получения `TECH_PLAN` запускай нужных архитекторов:
- `django-architect` — для Backend (читает секцию BACKEND SCOPE и API CONTRACT)
- `ios-architect` — для iOS (читает секцию iOS SCOPE и API CONTRACT)
- `android-architect` — для Android (читает секцию ANDROID SCOPE и API CONTRACT)

Рекомендуемый порядок: сначала `django-architect` чтобы зафиксировать API, затем платформенные.
