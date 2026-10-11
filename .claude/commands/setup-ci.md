---
name: "setup-ci"
description: Создать или улучшить GitLab CI/CD пайплайн. Включает стадии тестирования, сборки Docker-образа и деплоя на staging/production.
version: "1.0.0"
profile: "pack:devops"
tags: ["devops", "ci-cd", "gitlab"]
orchestrates: ["devops-engineer"]
example_prompt: "/setup-ci"
---

Запусти агент `devops-engineer` для настройки GitLab CI/CD.

$ARGUMENTS

Агент должен:
1. Проверить наличие `.gitlab-ci.yml` — если есть, улучшить; если нет — создать
2. Настроить стадии: test → build → deploy
3. Добавить coverage report в артефакты
4. Настроить деплой на staging (автоматический) и production (ручной)
5. Указать какие GitLab Variables нужно настроить в проекте
