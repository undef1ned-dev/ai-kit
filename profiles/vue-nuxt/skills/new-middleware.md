---
name: "new-middleware"
description: Создать новый Nuxt route middleware для auth, redirect или navigation policy
version: "1.0.0"
profile: "vue-nuxt"
tags: ["vue", "nuxt", "middleware", "routing", "auth"]
orchestrates: []
example_prompt: "/new-middleware auth"
---

Создай новый route middleware для Vue/Nuxt.

Запроси у пользователя:
1. Имя middleware
2. Для какого сценария он нужен: auth, guest-only, onboarding, locale, feature gating
3. На каких маршрутах он должен работать
4. Какие redirect или abort правила ожидаются

Перед scaffold:
- изучи существующие `components/`, `composables/`, `stores/` и похожие файлы проекта
- проверь, нет ли уже похожего guard-flow, auth pattern или навигационного контракта

Создай файл `middleware/<name>.ts`.

Требования:
- используй стандартный Nuxt route middleware pattern
- не дублируй store/page логику, если middleware должен только принять навигационное решение
- избегай redirect loops
- учитывай SSR и client navigation
- если нужен auth state, опирайся на существующий store/composable проекта

После создания:
1. Покажи contract middleware
2. Объясни, почему это middleware, а не page-level check
3. Предложи test cases для allowed, redirected и edge-case навигации
