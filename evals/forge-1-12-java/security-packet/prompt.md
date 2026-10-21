---
description: /security-check зовёт специалиста security профиля — пакет без серверных проверок, работа с миром в сетевом потоке, клиентский класс в общем коде ломает выделенный сервер
tags: [forge-1-12-java]
plugins: ["../../..", "../../../profiles/forge-1-12-java"]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Agent]
---

/security-check src/main/java/com/example/examplemod/network/ — мод пойдёт на публичный сервер, проверь сетевой код.
