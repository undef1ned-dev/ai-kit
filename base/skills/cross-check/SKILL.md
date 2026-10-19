---
name: "cross-check"
description: "Проанализировать, как изменение API или контракта влияет на другую сторону (backend и клиенты), и составить список нужных правок. Используй, когда меняется API, формат данных или контракт между проектами."
argument-hint: "<что изменилось>"
version: "1.0.0"
profile: "base"
tags: ["analysis", "cross-platform", "api"]
orchestrates: ["cross-project-analyst"]
example_prompt: "/cross-check изменился endpoint POST /api/v1/auth/login"
---

Запусти агент `cross-project-analyst` для анализа кросс-проектного влияния.

$ARGUMENTS

Агент должен:
1. Определить что изменилось (endpoint, модель данных, API-контракт)
2. Найти затронутые компоненты на другой стороне (backend ↔ iOS)
3. Проверить обратную совместимость
4. Предложить стратегию миграции
5. Сформировать список задач для обеих сторон

Примеры использования:
- `/cross-check Изменился endpoint /api/v1/users/ — добавлено поле avatar_url`
- `/cross-check iOS нужен endpoint для получения списка уведомлений`
- `/cross-check Проверить совместимость моделей User между проектами`
