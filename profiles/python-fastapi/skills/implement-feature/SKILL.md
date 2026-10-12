---
name: "implement-feature"
template: "implement-feature"
profile: "python-fastapi"
tags: ["fastapi", "python", "implementation"]
orchestrates: ["fastapi-architect", "fastapi-coder", "fastapi-tester", "fastapi-reviewer"]
example_prompt: "/implement-feature роутер уведомлений с WebSocket"
tvar_PLATFORM: FastAPI
tvar_PREFIX: fastapi
tvar_TESTER_DESC: "async pytest тесты для Service и API"
tvar_TAGS: '"fastapi", "python", "implementation"'
tvar_ORCHESTRATES: '"fastapi-architect", "fastapi-coder", "fastapi-tester", "fastapi-reviewer"'
tvar_EXAMPLE_PROMPT: "/implement-feature роутер уведомлений с WebSocket"
---

Реализуй фичу через цепочку специализированных FastAPI-агентов.

Фича: $ARGUMENTS

## Entry Surface Class

`/implement-feature` is the `primary task entry` for normal FastAPI delivery.

Use it when the task is implementation-first and should go through the canonical `fastapi-architect -> fastapi-coder -> fastapi-tester -> fastapi-reviewer` chain. Specialist logic stays inside the chain as a bounded overlay, not as a separate start surface.

## Контекст перед реализацией

Перед запуском агентов собери:
- API surface manifest and existing routers/schemas/services/models;
- project evidence refs from runtime context;
- provider export packet refs, если фича пришла из Figma/GitHub context;
- current tests and migration state.

## Декомпозиция

ARCHITECT_PLAN должен разделить feature на:
- API contract decisions;
- schema/request/response changes;
- service boundary and dependency direction;
- persistence and migration impact;
- tests and validation gates.

## Шаг 1 — Архитектура (fastapi-architect)

Используй агент fastapi-architect:
- Прочитай main.py, models/, routers/
- Проверь схему БД через mcp__postgres__query (если в проекте подключён postgres MCP)
- Спроектируй: модели, Pydantic-схемы, Service, Router, миграции
- Выведи ARCHITECT_PLAN

ARCHITECT_PLAN обязан назвать service boundary, API contract decisions and test matrix.

Дождись результата.

## Шаг 2 — Overlay specialist (если нужен)

Если в `ARCHITECT_PLAN` есть `AGENT_NEEDED: да` для LangGraph scope:
- запусти `fastapi-langgraph-expert` как implementation-advisor overlay;
- получи `LANGGRAPH_IMPLEMENTATION_BRIEF`;
- передай этот brief в `fastapi-coder`, а затем держи его видимым для `fastapi-tester` и `fastapi-reviewer`.

`fastapi-langgraph-expert` не заменяет canonical `fastapi-architect -> fastapi-coder -> fastapi-tester -> fastapi-reviewer` spine.

## Шаг 3 — Реализация (fastapi-coder)

Используй агент fastapi-coder с ARCHITECT_PLAN:
- Реализуй все файлы по плану
- Подключи роутер в main.py
- Выведи CODER_RESULT

Дождись результата.

## Шаг 4 — Параллельно: тесты и ревью

Запусти одновременно:
- fastapi-tester — async pytest тесты для Service и API
- fastapi-reviewer — проверка на соответствие стандартам

## API contract decisions

Перед итогом проверь, что реализация явно фиксирует:
- routes, status codes and response_model;
- request/response schemas;
- auth and permission dependencies;
- persistence changes and migration command;
- error behavior for 401/404/409/422.

## Phase 33 backend examples

For a frontend-visible API change, ARCHITECT_PLAN must include:
- the exact response field or status behavior the frontend consumes;
- whether the change is backward-compatible and what default/empty state the frontend should render;
- service boundary ownership for the new rule;
- tests for service behavior, API response shape and frontend-visible empty/error contracts.

Do not hide the cross-stack contract inside router code. The service boundary remains the owner of business rules, and the router only maps HTTP dependencies and response models.

## Anti-patterns

Не принимай результат, если:
- implementation started before ARCHITECT_PLAN;
- specialist overlay tried to replace the canonical delivery chain;
- router contains business logic that belongs in service;
- schemas are reused across incompatible request/response boundaries;
- migration impact is implicit;
- tests do not cover service and API paths.

## Шаг 4 — Миграция (если нужна)

Если MIGRATION_NEEDED: да:
```bash
alembic revision --autogenerate -m "<slug>"
alembic upgrade head
```

## Шаг 5 — Итог

```
## Фича реализована: <название>

### API
<список эндпоинтов с методами и status_code>

### Созданные файлы
<список>

### Тесты
<список>

### Следующие шаги
alembic revision --autogenerate -m "<slug>"  # если нужна миграция
alembic upgrade head
pytest tests/ -v --asyncio-mode=auto
```

## Validation gates

Минимум:
```bash
pytest tests/ -v --asyncio-mode=auto
```
