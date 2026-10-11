---
name: "new-app"
description: Создать новое Django-приложение с полной структурой (models, admin, serializers, views, urls, tests)
version: "1.0.0"
profile: "python-django"
tags: ["django", "python", "scaffold"]
orchestrates: []
example_prompt: "/new-app notifications"
---

Создай новое Django-приложение.

Название приложения: $ARGUMENTS

## Контекст перед реализацией

Перед scaffold проверь:
- `profiles/python-django/api-surface.manifest.json`;
- существующие `apps/`, `config/settings/`, `config/urls.py`;
- app boundaries, naming conventions and installed app order;
- project evidence refs from runtime context, если они есть.

Не создавай app, пока не понятно, нужен ли DRF API, admin-only surface, background workflow or persistence-only module.

## Декомпозиция

Разделяй ответственность так:
- `models.py` — persistence model and simple invariants;
- `services.py` — business use cases and cross-model orchestration, если нужна логика;
- `serializers.py` — request/response validation for DRF;
- `views.py` — ViewSet/API transport boundary;
- `admin.py` — staff workflow and visibility, not business rules;
- `tests/` — API, service and admin smoke coverage where relevant.

App boundary обязателен: новая app должна иметь понятную ownership area and not duplicate existing apps.

## API contract decisions

Перед кодом выведи:
- app responsibility and public API surface;
- models and relations;
- serializers/viewsets/urls if API exists;
- admin behavior;
- migration and test commands.

Создай следующую структуру:
```
apps/<name>/
  migrations/
    __init__.py
  __init__.py
  admin.py           — ModelAdmin с list_display, search, filter
  apps.py            — настройки приложения
  models.py          — базовая модель с created_at/updated_at
  views.py           — ModelViewSet
  urls.py            — DefaultRouter с ViewSet
  tests/
    __init__.py
    factories.py     — factory_boy фабрика
    test_api.py      — API тесты
```

Зарегистрируй приложение в config/settings/base.py.
Подключи urls.py в config/urls.py.

## Phase 33 backend examples

For a large-domain app split decision, explain:
- why the new app owns this domain instead of extending an existing app;
- which cross-app dependency is allowed and which direction is forbidden;
- whether shared queries belong in `services.py` instead of models or viewsets;
- how URL namespace, serializer ownership and migration boundaries remain clear.

If ownership is unclear, stop before scaffold and ask for decomposition rather than creating a convenience app.

## Anti-patterns

Не делай:
- fat models with workflow logic that belongs in services;
- API viewsets without serializers/tests;
- admin registration without list/search/filter basics;
- app creation without adding it to settings;
- migrations without rollback awareness.

## Validation gates

Минимум:
```bash
python manage.py makemigrations <app>
python manage.py migrate
pytest apps/<name>/tests -v
```

После создания покажи API контракт и как запустить тесты.
