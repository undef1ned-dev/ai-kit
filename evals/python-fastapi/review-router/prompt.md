---
description: Ревью роутера с заложенными ошибками — SQL-инъекция, блокирующие requests и time.sleep в async, голый except, нет response_model
tags: [python-fastapi]
plugins: ["../../..", "../../../profiles/python-fastapi"]
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Agent]
---

Проверь routers/users.py перед мержем и перечисли, что нужно исправить.
