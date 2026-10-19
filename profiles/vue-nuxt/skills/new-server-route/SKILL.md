---
name: "new-server-route"
description: "Создать Nitro server route для BFF или proxy-логики с валидацией запроса и безопасной обработкой ответа. Используй, когда нужен эндпоинт в server/api."
argument-hint: "<путь.метод>"
version: "1.0.0"
profile: "vue-nuxt"
tags: ["vue", "nuxt", "nitro", "server-api", "bff"]
orchestrates: []
example_prompt: "/new-server-route notifications/index.get"
---

Создай новый Nitro server route.

Запроси у пользователя:
1. Путь route
2. HTTP method
3. Что route должен делать: proxy, aggregation, normalization, auth-aware endpoint
4. Какие входные параметры и какой shape ответа нужен

Перед scaffold:
- изучи существующие `components/`, `composables/`, `stores/` и похожие файлы проекта
- проверь, какие contracts, proxy-patterns и связанные frontend artifacts уже есть в проекте

Создай файл `server/api/<path>.<method>.ts`.

Требования:
- используй стандартный Nitro route handler pattern
- UI-логика запрещена: только server-side orchestration
- явно обработай ошибки и shape ответа
- если route пробрасывает auth/cookies/headers, сделай это осознанно и безопасно
- если это простой proxy, не усложняй без причины

После создания:
1. Покажи contract route
2. Объясни, почему здесь нужен `server/api`, а не прямой запрос из клиента
3. Предложи test cases для happy path и error path
