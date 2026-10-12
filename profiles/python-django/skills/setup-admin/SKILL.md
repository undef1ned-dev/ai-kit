---
name: "setup-admin"
description: "Настроить расширенный Django Admin для существующей модели: списки, фильтры, поиск, inline, actions. Используй, когда пользователь просит админку для модели."
version: "1.0.0"
profile: "python-django"
tags: ["django", "admin"]
orchestrates: ["django-architect", "django-admin-expert", "django-coder", "django-tester", "django-reviewer"]
example_prompt: "/setup-admin Contract"
---

Запусти canonical Django delivery flow для настройки Admin. `django-admin-expert` в этом skill работает как bounded overlay и не заменяет `django-architect -> django-coder -> django-tester -> django-reviewer`.

Модель: $ARGUMENTS

## Entry Surface Class

`/setup-admin` is a `specialist overlay start`.

Use it only when admin behavior is the primary scope of the task. If the request is broader implementation work with optional admin impact, fall back to `/implement-feature` as the primary task entry and let the admin overlay activate inside that chain.

## Overlay contract

`django-admin-expert` обязан вернуть `ADMIN_IMPLEMENTATION_BRIEF`:
- c operator workflow, query/performance notes and safe action constraints;
- c границами Service-layer и permission notes;
- как вход в canonical Django delivery spine, а не как альтернативный исполнитель.

## Контекст перед реализацией

Перед изменением `admin.py` проверь:
- модель, related fields and indexes;
- existing admin registrations;
- staff workflow: search, filtering, audit, readonly fields;
- service methods that may back safe admin actions.

## Декомпозиция

Разделяй admin responsibilities:
- ModelAdmin display/search/filter/read-only configuration;
- query optimization with `list_select_related`, `prefetch_related` or annotations;
- safe actions that delegate to Service methods;
- inline models only when they support the staff workflow.

Admin boundary обязателен: Django Admin should expose operational control, not become the business service layer.

## API contract decisions

Даже если public API не меняется, опиши:
- whether admin-only behavior changes persistence state;
- which Service method backs each action;
- permissions/staff constraints;
- query impact for list/detail admin pages.

Порядок работы:
1. `django-architect` фиксирует `ARCHITECT_PLAN` с app boundary, admin impact, validation gates и touched files
2. `django-admin-expert` читает `ARCHITECT_PLAN` и возвращает `ADMIN_IMPLEMENTATION_BRIEF`
3. `django-coder` реализует `admin.py` и связанные Service/model changes, используя `ARCHITECT_PLAN` + `ADMIN_IMPLEMENTATION_BRIEF`
4. `django-tester` проверяет admin, service and API regressions
5. `django-reviewer` завершает risk/release judgment по `CODER_RESULT`, `TESTER_RESULT` и `ADMIN_IMPLEMENTATION_BRIEF`

## Phase 33 backend examples

For a heavy admin list page, include an admin performance review:
- use `get_queryset`, `list_select_related`, `prefetch_related` or annotations for relation-heavy `list_display`;
- keep staff-only search fields explicit and indexed where needed;
- make audit fields readonly;
- route state-changing actions through Service methods and name permission constraints.

Do not add computed columns or bulk actions without query and permission impact notes.

## Anti-patterns

Не делай:
- `django-admin-expert` as a replacement for canonical delivery flow;
- unsafe bulk actions without confirmation or Service delegation;
- expensive computed columns without query optimization;
- editable audit fields;
- admin logic that bypasses domain validation;
- missing search/filter for operational models.

## Validation gates

Минимум:
```bash
pytest -k admin -v
python manage.py check
```

Результат: готовый admin.py с полноценным ModelAdmin.
