---
description: Django-приложение по правилам профиля — модель с FK на пользователя, админка, DRF API с правами и select_related, подключение в INSTALLED_APPS
tags: [python-django]
plugins: ["../../..", "../../../profiles/python-django"]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Write, Edit]
---

Создай Django-приложение apps/comments: комментарии к статьям (apps.articles.Article), автор — пользователь. Нужны модель, админка и DRF API: список комментариев статьи и создание комментария авторизованным пользователем. Подключи приложение в настройки и urls. Все детали здесь, уточнять ничего не нужно.
