---
name: "setup-ci"
description: "Создать или улучшить CI/CD-пайплайн (GitHub Actions или GitLab CI): проверки командами профиля, сборка Docker-образа, деплой на staging и production. Используй, когда пользователь просит настроить CI/CD."
argument-hint: "[CI-система или окружения]"
version: "2.0.0"
profile: "pack:devops"
tags: ["devops", "ci-cd", "github-actions", "gitlab"]
orchestrates: ["devops-engineer"]
example_prompt: "/setup-ci"
---

Запусти агент `devops-engineer` для настройки CI/CD.

$ARGUMENTS

Агент должен:
1. Взять стек, `root` и команды `install`, `lint`, `test`, `build` профилей из `.aikit/profiles.json`
2. Определить CI-систему по проекту (`.github/workflows/`, `.gitlab-ci.yml`, git remote) или по аргументу; если не ясно — вернуть `QUESTIONS`
3. Улучшить существующий пайплайн или создать новый: проверки → сборка образа → деплой
4. Настроить деплой на staging (автоматический) и production (ручной)
5. Перечислить секреты, которые нужно завести в настройках CI

Если агент вернул `QUESTIONS` — задай их пользователю и запусти `devops-engineer` снова с ответами.
