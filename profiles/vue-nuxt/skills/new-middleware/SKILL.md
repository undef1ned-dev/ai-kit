---
name: "new-middleware"
description: "Создать Nuxt route middleware для auth, redirect или navigation policy. Используй, когда нужна защита или перенаправление маршрутов."
argument-hint: "<имя>"
version: "1.0.0"
profile: "vue-nuxt"
tags: ["vue", "nuxt", "middleware", "routing", "auth"]
orchestrates: []
example_prompt: "/new-middleware auth"
---

Создай новый route middleware `middleware/<name>.ts`.

Запроси у пользователя то, чего нет в задаче:
1. Имя middleware
2. Для какого сценария он нужен: auth, guest-only, onboarding, locale, feature gating
3. На каких маршрутах он должен работать
4. Какие правила redirect или abort ожидаются

## Перед созданием

- Изучи существующие `middleware/`, `stores/`, `composables/` и страницы, которые middleware будет защищать
- Проверь, нет ли уже похожего guard: auth-проверки, redirect-правила, глобального middleware

## Требования

- стандартный Nuxt route middleware через `defineNuxtRouteMiddleware`
- middleware только принимает навигационное решение и не дублирует логику store или страницы
- без циклических redirect
- одинаково корректен при SSR и при навигации на клиенте
- auth state — из существующего store или composable проекта

## После создания

1. Запусти `lint` и `format` профиля из `.aikit/profiles.json` на созданных файлах (в папке `root` профиля, пути вместо `{files}`); если добавил тест — и `test`
2. Покажи, на каких маршрутах и с какими правилами работает middleware, и объясни, почему это middleware, а не проверка на странице
3. Предложи тестовые кейсы: доступ разрешён, redirect, граничные случаи навигации
