---
name: "dockerize"
description: "Создать Dockerfile, docker-compose.yml и .dockerignore под стек проекта. Используй, когда пользователь просит упаковать проект в Docker."
version: "1.0.0"
profile: "pack:devops"
tags: ["devops", "docker"]
orchestrates: ["devops-engineer"]
example_prompt: "/dockerize"
---

Запусти агент `devops-engineer` для создания Docker-конфигурации.

$ARGUMENTS

Агент должен:
1. Определить стек из `CLAUDE.md`
2. Создать `Dockerfile` с непривилегированным пользователем и healthcheck
3. Создать `docker-compose.yml` с БД и зависимостями
4. Создать `.dockerignore`
5. Проверить что секреты подключаются только через переменные окружения
