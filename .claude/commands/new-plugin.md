---
name: "new-plugin"
description: Создать новый Nuxt plugin для app-level интеграции, provide/inject или инициализации зависимости
version: "1.0.0"
profile: "vue-nuxt"
tags: ["vue", "nuxt", "plugin", "provide", "injection"]
orchestrates: []
example_prompt: "/new-plugin analytics.client"
---

Создай новый Nuxt plugin.

Запроси у пользователя:
1. Имя plugin
2. Что он должен предоставлять: SDK, helper, analytics, formatter, API client
3. Нужен ли `client`, `server` или универсальный scope
4. Какой публичный contract должен быть доступен приложению

Перед scaffold:
- изучи существующие `components/`, `composables/`, `stores/` и похожие файлы проекта
- проверь существующие runtime patterns, provide/inject контракты и пересечения с composables

Создай файл `plugins/<name>.ts`.

Требования:
- используй стандартный Nuxt plugin pattern
- если plugin должен быть только на клиенте или сервере, вырази это именованием файла
- `provide` и injection должны быть понятными и типобезопасными
- избегай тяжёлых глобальных side effects без необходимости
- не смешивай plugin setup с page/business logic

После создания:
1. Покажи публичный contract plugin
2. Объясни, почему это plugin, а не composable
3. Предложи test cases для injection, scope и startup behaviour
