---
name: git-branch
description: "Convention for naming git branches in this repository: Conventional Branch 1.1.0. MUST be followed whenever a branch is created or renamed — always, automatically, without the user having to ask. Trigger whenever you are about to run `git checkout -b`, `git switch -c`, `git branch <name>`, `git branch -m`, create a worktree with a new branch, or when the user says «создай ветку», «новая ветка», «branch», «переименуй ветку». Defines branch types, naming rules and which base branch to start from."
---

# Именование веток — Conventional Branch

Все ветки именуются по спецификации
[Conventional Branch 1.1.0](https://conventionalbranch.org/).
Применяй её **всегда и автоматически**, даже без явной просьбы пользователя.

## Формат

```
<type>/<description>
```

## Типы

| type       | Когда использовать                                   | Откуда ветвиться                   |
|------------|------------------------------------------------------|------------------------------------|
| `feat`     | Новая функциональность (полная форма — `feature`)    | `develop`, если есть, иначе `main` |
| `fix`      | Исправление бага (полная форма — `bugfix`)           | `develop`, если есть, иначе `main` |
| `hotfix`   | Срочное исправление в проде                          | `main` (потом влить и в `develop`) |
| `release`  | Подготовка релиза                                    | `develop`, если есть, иначе `main` |
| `chore`    | Служебное: зависимости, конфиги, CI, документация    | `develop`, если есть, иначе `main` |

- Спецификация допускает и короткую, и полную форму. В репозитории
  используем **короткие** `feat/` и `fix/` — они совпадают с типами коммитов.
- Ветки `main`, `master`, `develop` — trunk, префикса не имеют.
- Спецификация также описывает префиксы AI-агентов (`ai/`, `claude/`,
  `codex/`, `copilot/`, `cursor/`). Используй их, только если пользователь
  явно попросил; по умолчанию — тип по смыслу задачи.

## Правила для description

1. Только строчная латиница `a-z`, цифры `0-9` и дефис `-` между словами.
   Заглавные буквы, `_`, пробелы и кириллица запрещены.
2. Точка допустима для номера версии: `release/v1.2.0`.
3. Дефис и точка не идут подряд и не стоят в начале или конце description.
4. Коротко, но понятно, о чём работа: 2–5 слов на английском.
5. Номер задачи, если он есть, включается в description:
   `feat/issue-42-oauth-login`, `fix/proj-123-email-validation`.

## Примеры

```
feat/oauth-login
feat/issue-42-csv-report-export
fix/empty-list-crash
fix/proj-123-email-validation
hotfix/memory-leak-on-requests
release/v2.0.0
chore/update-dependencies
chore/ci-test-pipeline
```

## Поведение агента

- Одна задача — одна ветка. Не коммить напрямую в `main` / `develop`.
- Если тип или description неочевидны из задачи — предложи 2–3 варианта
  имени и дождись выбора пользователя. Если очевидны — создавай ветку сразу
  и сообщи её имя.
