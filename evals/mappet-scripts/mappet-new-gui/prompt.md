---
description: Реализация Mappet GUI по образцу проекта с колонкой, callback и константами
tags: [mappet-scripts]
plugins: ["../../..", "../../../profiles/mappet-scripts"]
max_turns: 35
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Agent, Write, Edit]
---

Сделай src/gui/bank/BankAccountSelect.ts по образцу src/gui/bank/BankBalance.ts. Это учебный экран выбора счёта: заголовок «Выбор счёта», одна кнопка «Личный счёт» с ID personal-account, нажатие закрывает окно. Окно личное. Используй специалиста GUI из профиля, запуск разрешаю. Каталога мира в этой фикстуре нет, укажи metadata в отчёте.
