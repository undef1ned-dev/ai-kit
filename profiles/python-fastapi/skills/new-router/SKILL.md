---
name: "new-router"
description: "Создать FastAPI-роутер с полной CRUD-структурой: модель, схемы, сервис, роутер, тесты. Используй, когда нужен новый ресурс или группа эндпоинтов."
version: "1.0.0"
profile: "python-fastapi"
tags: ["fastapi", "python", "scaffold"]
orchestrates: []
example_prompt: "/new-router notifications"
---

Создай новый FastAPI роутер.

Название ресурса: $ARGUMENTS

## Контекст перед реализацией

Перед созданием файлов проверь:
- `profiles/python-fastapi/api-surface.manifest.json` и существующие `routers/`, `schemas/`, `services/`, `models/`;
- текущие dependency patterns для `get_session`, `get_current_user`, pagination и error handling;
- связанные project evidence refs, если runtime передал backend или provider context.

Не начинай scaffold, пока не понятно, какой API contract нужен: collection endpoint, detail endpoint, command endpoint или nested resource.

## Декомпозиция

Разделяй ответственность так:
- `routers/<name>.py` — HTTP contract, dependencies, status codes, response_model;
- `schemas/<name>.py` — request/response DTO, validation and OpenAPI shape;
- `services/<name>.py` — business rules, authorization decisions that are not pure transport concerns, persistence orchestration;
- `models/<name>.py` — SQLAlchemy persistence model only;
- `tests/test_<name>.py` — API and service behavior.

Service boundary обязателен: router не должен содержать business logic кроме dependency wiring and response mapping.

## API contract decisions

Перед кодом выведи краткий контракт:
- routes with method, path, status_code and response_model;
- request schemas and response schemas;
- auth requirement;
- error cases: 401, 404, 409/422 where relevant;
- persistence and migration impact.

Создай следующую структуру:
```
models/<name>.py          — SQLAlchemy 2.0 ORM-модель
routers/<name>.py         — APIRouter с CRUD endpoints
schemas/<name>.py         — Pydantic v2 схемы (Create, Update, Response)
services/<name>.py        — Service-класс с бизнес-логикой
tests/test_<name>.py      — async pytest тесты
```

Требования:
- Модель: Mapped[] + mapped_column() (SQLAlchemy 2.0 style)
- Схемы: отдельные Create / Update / Response, model_config = ConfigDict(from_attributes=True)
- Service: async методы list(), get_or_404(), create(), update(), delete()
- Router: response_model, status_code, Depends(get_session), Depends(get_current_user)
- Тесты: AsyncClient + ASGITransport, in-memory SQLite, покрыть 200/201/204/401/404/422

## Phase 33 backend examples

Если route зависит от captured provider evidence, сначала зафиксируй provider evidence contract как review-required context:
- назови provider packet или handoff ref и ограничения источника;
- сравни fields с API surface manifest, не копируй provider shape в response schema напрямую;
- если provider evidence conflicts with API surface, остановись и запроси contract decision;
- добавь тест на absent provider field и 422 schema validation.

Memory rule: provider evidence can inform the route, but review-required memory promotion is needed before turning it into durable API knowledge.

## Anti-patterns

Не делай:
- business logic directly in router handlers;
- one schema reused for create, update and response;
- endpoint without explicit response_model and status_code;
- service methods that silently swallow missing resources;
- tests that only check happy path.

После создания:
1. Добавь роутер в main.py: `app.include_router(router)`
2. Создай миграцию: `alembic revision --autogenerate -m "краткое_описание_на_английском"`
3. Примени: `alembic upgrade head`

## Validation gates

Минимум:
```bash
pytest tests/test_<name>.py -v --asyncio-mode=auto
alembic upgrade head
```

Покажи API контракт и команду для запуска тестов.
