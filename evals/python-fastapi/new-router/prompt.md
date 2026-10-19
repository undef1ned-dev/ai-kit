---
description: Роутер по правилам профиля — async, Depends(get_session), response_model, логика в сервисе, схемы отдельно
tags: [python-fastapi]
plugins: ["../../..", "../../../profiles/python-fastapi"]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Agent, Write, Edit]
---

Добавь эндпоинты уведомлений: список уведомлений пользователя и отметка уведомления прочитанным. Роутер положи в routers/notifications.py и подключи в main.py. Аутентификации в проекте пока нет — id пользователя передавай параметром. Все детали здесь, уточнять ничего не нужно.
