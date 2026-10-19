---
name: "dockerize"
description: "Создать Dockerfile, docker-compose.yml и .dockerignore под стек и команды профиля проекта. Используй, когда пользователь просит упаковать проект в Docker."
argument-hint: "[стек или особенности сборки]"
version: "2.0.0"
profile: "pack:devops"
tags: ["devops", "docker"]
orchestrates: ["devops-engineer"]
example_prompt: "/dockerize"
---

Запусти агент `devops-engineer` для создания Docker-конфигурации.

$ARGUMENTS

Агент должен:
1. Взять стек, `root` и команды `install`, `build`, `run` профилей из `.aikit/profiles.json`
2. Создать `Dockerfile` (multi-stage при сборке, непривилегированный пользователь, закреплённые версии, healthcheck)
3. Создать `docker-compose.yml` с теми зависимостями, которые проект действительно использует
4. Создать `.dockerignore`
5. Проверить, что секреты подключаются только через переменные окружения
