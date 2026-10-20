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

Создай новый Nitro server route `server/api/<path>.<method>.ts`.

Запроси у пользователя то, чего нет в задаче:
1. Путь route
2. HTTP method
3. Что route должен делать: proxy, агрегация, нормализация ответа, endpoint с авторизацией
4. Какие входные параметры и какая форма ответа нужны

## Перед созданием

- Изучи существующие `server/api/`, `server/utils/` и клиентский код, который будет вызывать route
- Проверь, нет ли уже route или proxy с тем же назначением

## Требования

- стандартный Nitro handler через `defineEventHandler`
- только серверная логика, без UI-логики
- входные параметры проверены, ошибки и форма ответа обработаны явно
- auth, cookies и заголовки пробрасываются осознанно и без утечки токенов клиенту
- простой proxy не усложнять без причины

## После создания

1. Запусти `lint` и `format` профиля из `.aikit/profiles.json` на созданных файлах (в папке `root` профиля, пути вместо `{files}`); если добавил тест — и `test`
2. Покажи контракт route — вход, ответ, ошибки — и объясни, почему здесь нужен `server/api`, а не прямой запрос из клиента
3. Предложи тестовые кейсы: happy path и error path
