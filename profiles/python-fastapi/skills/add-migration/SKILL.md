---
name: "add-migration"
description: "Сгенерировать и применить Alembic-миграцию для изменений в моделях SQLAlchemy. Используй после изменения моделей или когда пользователь просит миграцию."
version: "1.0.0"
profile: "python-fastapi"
tags: ["fastapi", "python", "alembic", "database"]
orchestrates: []
example_prompt: "/add-migration добавить таблицу уведомлений"
---

Создай и примени Alembic-миграцию.

Описание изменения: $ARGUMENTS

## Контекст перед реализацией

Перед генерацией миграции проверь:
- измененные `models/` and SQLAlchemy metadata;
- текущий head в `migrations/versions/`;
- API contract impact: renamed fields, nullable changes, defaults, indexes;
- service and schema code paths that read or write the changed persistence surface.

## Декомпозиция

Раздели работу на:
- model diff;
- generated migration review;
- service/schema compatibility check;
- rollback path;
- tests or smoke command for affected behavior.

Migration boundary обязателен: миграция не должна подменять service-layer behavior or API validation.

## Шаг 1 — Проверь модели

Прочитай изменённые файлы в models/ чтобы понять что изменилось.

## Шаг 2 — Сгенерируй миграцию

```bash
alembic revision --autogenerate -m "<краткое_описание_на_английском>"
```

Прочитай сгенерированный файл в migrations/versions/ и проверь:
- Все нужные поля присутствуют в upgrade()
- downgrade() корректно откатывает изменения
- Нет лишних изменений (alembic иногда подхватывает несвязанные таблицы)

## API contract decisions

Перед применением миграции явно опиши:
- whether request/response schemas change;
- whether old clients remain compatible;
- whether backfill/default is needed;
- whether endpoint status/error behavior changes.

## Phase 33 backend examples

Для risky schema change добавь rollback decision перед `alembic upgrade head`:
- nullable-to-required changes require backfill/default and a compatibility note that old clients remain compatible or a breaking-change stop;
- destructive rename/drop requires explicit review of generated `upgrade()` and `downgrade()`;
- service/schema compatibility must be checked before applying migration;
- validation should include the affected API or service smoke path, not only `alembic current`.

## Шаг 3 — Примени миграцию

```bash
alembic upgrade head
```

## Шаг 4 — Убедись что всё применилось

```bash
alembic current
```

## Anti-patterns

Не делай:
- destructive column/table changes without explicit review note;
- migration that changes data shape but leaves schemas/services stale;
- generated migration with unrelated table churn;
- no-op downgrade;
- applying migration before reading generated operations.

## Validation gates

Минимум:
```bash
alembic revision --autogenerate -m "<slug>"
alembic upgrade head
alembic current
```

Покажи путь к созданному файлу миграции и краткое содержание upgrade/downgrade.
