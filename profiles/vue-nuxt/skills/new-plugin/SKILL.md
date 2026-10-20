---
name: "new-plugin"
description: "Создать Nuxt plugin для app-level интеграции, provide/inject или инициализации зависимости. Используй, когда библиотеку или сервис нужно подключить на уровне приложения."
argument-hint: "<имя>"
version: "1.0.0"
profile: "vue-nuxt"
tags: ["vue", "nuxt", "plugin", "provide", "injection"]
orchestrates: []
example_prompt: "/new-plugin analytics.client"
---

Создай новый Nuxt plugin `plugins/<name>.ts`.

Запроси у пользователя то, чего нет в задаче:
1. Имя plugin
2. Что он должен предоставлять: SDK, helper, analytics, formatter, API client
3. Нужен ли `client`, `server` или универсальный scope
4. Какой публичный API должен быть доступен приложению

## Перед созданием

- Изучи существующие `plugins/`, `composables/` и `nuxt.config.*`
- Проверь, нет ли уже такой интеграции: plugin, модуль Nuxt или composable с тем же `provide`

## Требования

- стандартный Nuxt plugin через `defineNuxtPlugin`
- plugin только на клиенте или только на сервере — суффикс `.client` или `.server` в имени файла
- `provide` и injection понятные и типизированные
- без тяжёлых глобальных побочных эффектов при старте, если они не нужны
- без логики страниц и бизнес-логики внутри plugin

## После создания

1. Запусти `lint` и `format` профиля из `.aikit/profiles.json` на созданных файлах (в папке `root` профиля, пути вместо `{files}`); если добавил тест — и `test`
2. Покажи публичный API plugin и объясни, почему это plugin, а не composable
3. Предложи тестовые кейсы: injection, scope, поведение при старте
