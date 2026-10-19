---
name: "cross-check"
description: "Проанализировать, как изменение API или контракта влияет на другую сторону (backend и клиенты), и составить список нужных правок. Используй, когда меняется API, формат данных или контракт между проектами."
argument-hint: "<что изменилось>"
version: "2.0.0"
profile: "base"
tags: ["analysis", "cross-platform", "api"]
orchestrates: ["cross-project-analyst"]
example_prompt: "/cross-check изменился endpoint POST /api/v1/auth/login"
---

Запусти агент `cross-project-analyst` для анализа кросс-проектного влияния.

$ARGUMENTS

Агент должен:
1. Определить что изменилось (endpoint, модель данных, API-контракт)
2. Найти затронутые компоненты на других сторонах — профили из `.aikit/profiles.json` и внешние клиенты из `PRODUCT.md`
3. Проверить обратную совместимость
4. Предложить стратегию миграции
5. Сформировать список задач для каждой стороны

Примеры использования:
- `/cross-check Изменился endpoint /api/v1/users/ — добавлено поле avatar_url`
- `/cross-check фронтенду нужен endpoint для получения списка уведомлений`
- `/cross-check Проверить совместимость моделей User между проектами`
