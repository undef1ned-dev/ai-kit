---
name: "implement-feature"
template: "implement-feature"
profile: "python-django"
tags: ["django", "python", "implementation"]
orchestrates: ["django-architect", "django-coder", "django-tester", "django-reviewer"]
example_prompt: "/implement-feature система уведомлений через Celery"
tvar_PLATFORM: Django
tvar_PREFIX: django
tvar_TESTER_DESC: "pytest тесты для Service и API"
tvar_TAGS: '"django", "python", "implementation"'
tvar_ORCHESTRATES: '"django-architect", "django-coder", "django-tester", "django-reviewer"'
tvar_EXAMPLE_PROMPT: "/implement-feature система уведомлений через Celery"
---

Реализуй фичу через цепочку специализированных Django-агентов.

Фича: $ARGUMENTS

## Entry Surface Class

`/implement-feature` is the `primary task entry` for normal Django delivery.

Use it when the task is implementation-first and should go through the canonical `django-architect -> django-coder -> django-tester -> django-reviewer` chain. If the task is explicitly admin-first, use `/setup-admin` as the specialist overlay start instead of pretending every request begins there.

## Контекст перед реализацией

Перед запуском агентов собери:
- Django API surface manifest and existing apps;
- app boundaries, settings and URL routing;
- admin impact and persistence/migration state;
- project evidence refs from runtime context.

## Декомпозиция

ARCHITECT_PLAN должен разделить feature на:
- app ownership and cross-app boundaries;
- API contract decisions;
- model/persistence changes;
- service layer and dependency direction;
- admin impact;
- tests and migration gates.

## Шаг 1 — Архитектура (django-architect)

Используй агент django-architect:
- Прочитай PRODUCT.md и существующие apps/
- Спроектируй: модели, API, Admin, Service-слой
- Выведи ARCHITECT_PLAN

ARCHITECT_PLAN обязан назвать app boundary, service boundary, API contract decisions and admin impact.

Дождись результата.

## Шаг 2 — Overlay specialist (если нужен)

Если `ARCHITECT_PLAN` фиксирует admin impact:
- запусти `django-admin-expert` как implementation-advisor overlay;
- получи `ADMIN_IMPLEMENTATION_BRIEF`;
- передай его в `django-coder`, а затем держи видимым для `django-tester` и `django-reviewer`.

`django-admin-expert` не заменяет canonical `django-architect -> django-coder -> django-tester -> django-reviewer` spine.

## Шаг 3 — Реализация (django-coder)

Используй агент django-coder с ARCHITECT_PLAN:
- Реализуй все файлы по плану
- Выведи CODER_RESULT

Дождись результата.

## Шаг 4 — Параллельно: тесты и ревью

Запусти одновременно:
- django-tester — pytest тесты для Service и API
- django-reviewer — проверка на соответствие стандартам

## API contract decisions

Перед итогом проверь:
- DRF routes/viewsets/serializers and status behavior;
- model fields, migrations and rollback;
- Service methods that own business rules;
- admin behavior and staff permissions;
- test matrix for API, service and admin where relevant.

## Phase 33 backend examples

For Celery-backed delivery, ARCHITECT_PLAN must name the Celery handoff:
- API returns accepted/current state without pretending the async task is complete;
- Service owns idempotency and duplicate task dispatch prevention;
- admin retry actions delegate to Service methods and record staff permissions;
- tests cover API acceptance, service idempotency and task enqueue behavior.

## Anti-patterns

Не принимай результат, если:
- specialist overlay tried to replace the canonical delivery chain;
- viewset contains business logic that belongs in service;
- feature crosses apps without explicit decomposition;
- admin behavior bypasses Service validation;
- migrations are generated but not reviewed;
- tests omit service or API behavior.

## Шаг 4 — Итог

```
## Фича реализована: <название>

### API
<список эндпоинтов>

### Django Admin
<что настроено>

### Созданные файлы
<список>

### Тесты
<список>

### Следующие шаги
python manage.py makemigrations <app>
python manage.py migrate
pytest tests/test_mod.py::TestClass::test_method
```

## Validation gates

Минимум:
```bash
python manage.py makemigrations
python manage.py migrate
pytest -v
```
