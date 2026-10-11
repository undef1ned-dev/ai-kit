# Agents And Skills Reference

This reference is generated from `base/`, `profiles/` and `packs/`. It is not the primary entry surface; start with `docs/index.html` for the generated start-working overview or `docs/public/start-here.md` for the task-first router, then use this page when you need to inspect available agents and skills.

## Recommended Human Entry Commands

Use these commands before direct agent mentions:

- `/aikit-bootstrap-project`
- `/implement-feature`
- `/design-implement`
- `/design-review`
- `/security-check`

## Entry Surface Classes

- `primary task entry` means the skill is a default task-first start after the user picks the task route.
- `specialist overlay start` means the skill is only correct when the task is explicitly overlay-scoped and the canonical workflow or no-delivery status is still explained.
- `reference or advanced` means the skill is not the first recommended start for a new task.

## Visible Command Contract

| Command | Entry | Use It When | Activates |
| --- | --- | --- | --- |
| `/aikit-bootstrap-project` | `primary task entry` | a repository is new or newly connected and discovery must happen before delivery. | no delivery chain; it emits BOOTSTRAP_REPORT and the first recommended task prompt. |
| `/implement-feature` | `primary task entry` | ordinary implementation work starts after the task is known. | architect -> coder -> tester -> reviewer for the selected profile. |
| `/design-implement` | `specialist overlay start` | design is the primary input for implementation. | a design bridge first, then the normal delivery chain. |
| `/design-review` | `specialist overlay start` | the task is review-first against a real design source. | a design specialist instead of the full delivery chain. |
| `/security-check` | `primary task entry` | the task is a security, auth, secrets or dependency risk audit. | the security-auditor review path. |

## Advanced Direct-Agent Usage

Direct agent usage is advanced. Use it for narrow debugging, focused review or a known orchestration sub-role. For normal work, prefer the skill command because it owns routing, context, validation and stop conditions.

## Agents

| Name | Owner | Description | Source |
| --- | --- | --- | --- |
| `cross-project-analyst` | `base:base` | Кросс-проектный аналитик. Анализирует влияние изменений между backend и iOS — когда меняется API, определяет что нужно обновить на другой стороне. Помогает с координацией. | `base/agents/cross-project-analyst.md` |
| `mvp-analyst` | `base:base` | MVP-аналитик уровня зрелого продукта. Принимает описание идеи и формирует структурированный анализ в docs/mvp/. Учитывает бизнес-кейс, существующую аудиторию, конкурентный контекст, rollout-стратегию и операционную готовность. Читает PRODUCT.md для контекста продукта. | `base/agents/mvp-analyst.md` |
| `security-auditor` | `base:base` | Аудитор безопасности. Проверяет код на OWASP Top 10, секреты в коде, проблемы с авторизацией, инъекции. Запускай перед релизом или после крупных изменений. | `base/agents/security-auditor.md` |
| `tech-planner` | `base:base` | Технический планировщик. Читает продуктовый MVP-документ и переводит его в технический план реализации по платформам. Определяет API-контракт, scope каждой платформы, порядок реализации. Используй после mvp-analyst, перед архитекторами. | `base/agents/tech-planner.md` |
| `ux-writer` | `base:base` | UX-копирайтер. Пишет и ревьюит тексты интерфейса — кнопки, ошибки, пустые состояния, онбординг, push-уведомления. Следит за консистентностью терминологии. | `base/agents/ux-writer.md` |
| `django-admin-expert` | `profile:python-django` | Django Admin overlay specialist. Картирует operator workflow и admin constraints перед canonical Django delivery chain. | `profiles/python-django/agents/django-admin-expert.md` |
| `django-architect` | `profile:python-django` | Django архитектор. Проектирует структуру фичи до написания кода. Используй перед любой новой функциональностью. | `profiles/python-django/agents/django-architect.md` |
| `django-coder` | `profile:python-django` | Django разработчик. Реализует файлы по ARCHITECT_PLAN. Используй после получения плана от архитектора. | `profiles/python-django/agents/django-coder.md` |
| `django-reviewer` | `profile:python-django` | Django code reviewer. Проверяет код по CODER_RESULT и TESTER_RESULT. | `profiles/python-django/agents/django-reviewer.md` |
| `django-tester` | `profile:python-django` | Django QA. Пишет pytest-django тесты по CODER_RESULT. Используй после реализации фичи. | `profiles/python-django/agents/django-tester.md` |
| `fastapi-architect` | `profile:python-fastapi` | FastAPI архитектор. Проектирует структуру фичи до написания кода. Используй перед любой новой функциональностью. | `profiles/python-fastapi/agents/fastapi-architect.md` |
| `fastapi-coder` | `profile:python-fastapi` | FastAPI разработчик. Реализует файлы по ARCHITECT_PLAN. Используй после получения плана от архитектора. | `profiles/python-fastapi/agents/fastapi-coder.md` |
| `fastapi-langgraph-expert` | `profile:python-fastapi` | LangGraph overlay specialist. Проектирует LangGraph scope и возвращает implementation brief для canonical FastAPI delivery chain. | `profiles/python-fastapi/agents/fastapi-langgraph-expert.md` |
| `fastapi-reviewer` | `profile:python-fastapi` | FastAPI code reviewer. Проверяет код по CODER_RESULT и TESTER_RESULT. | `profiles/python-fastapi/agents/fastapi-reviewer.md` |
| `fastapi-tester` | `profile:python-fastapi` | FastAPI QA. Пишет async pytest тесты по CODER_RESULT. Используй после реализации фичи. | `profiles/python-fastapi/agents/fastapi-tester.md` |
| `vue-architect` | `profile:vue-nuxt` | Vue/Nuxt архитектор. Проектирует структуру frontend-фичи до написания кода. Используй перед новой страницей, клиентским flow или сложным состоянием. | `profiles/vue-nuxt/agents/vue-architect.md` |
| `vue-coder` | `profile:vue-nuxt` | Vue/Nuxt разработчик. Реализует файлы по ARCHITECT_PLAN. Используй после получения плана от vue-architect. | `profiles/vue-nuxt/agents/vue-coder.md` |
| `vue-design-bridge` | `profile:vue-nuxt` | Мост между дизайном и Vue/Nuxt кодом. Проверяет соответствие UI kit, дизайн-токенов и Figma-макетов, подсказывает правильные компоненты и паттерны реализации. | `profiles/vue-nuxt/agents/vue-design-bridge.md` |
| `vue-reviewer` | `profile:vue-nuxt` | Vue/Nuxt code reviewer. Проверяет код по CODER_RESULT и TESTER_RESULT. | `profiles/vue-nuxt/agents/vue-reviewer.md` |
| `vue-tester` | `profile:vue-nuxt` | Vue/Nuxt QA. Пишет unit и component тесты по CODER_RESULT, при необходимости предлагает E2E-проверку через Playwright. | `profiles/vue-nuxt/agents/vue-tester.md` |
| `ai-architect` | `pack:ai` | AI-архитектор. Проектирует LLM-интеграции, агентные пайплайны и RAG-системы. Используй когда нужно добавить AI-функциональность в продукт — чат, генерацию контента, автоматизацию через LLM. | `packs/ai/agents/ai-architect.md` |
| `prompt-engineer` | `pack:ai` | Промпт-инженер. Пишет, тестирует и оптимизирует системные промпты для LLM-интеграций. Выявляет edge cases, улучшает точность и консистентность ответов. | `packs/ai/agents/prompt-engineer.md` |
| `devops-engineer` | `pack:devops` | DevOps инженер. Проектирует Docker-конфигурации, GitLab CI/CD пайплайны, deployment стратегии. Используй когда нужно настроить инфраструктуру или автоматизировать процесс доставки. | `packs/devops/agents/devops-engineer.md` |
| `quality-analyst` | `pack:quality` | Аналитик качества кода. Оценивает покрытие тестами, выявляет технический долг и код-смелл, предлагает конкретные улучшения с приоритизацией по импакту. | `packs/quality/agents/quality-analyst.md` |

## Skills

| Name | Owner | Entry | Description | Orchestrates | Source |
| --- | --- | --- | --- | --- | --- |
| `analyze-mvp` | `base:base` | reference or advanced | Проанализировать MVP-идею уровня зрелого продукта. Агент проводит структурированное интервью, предлагает несколько вариантов продуктового подхода на выбор, затем делает полный анализ выбранного варианта — бизнес-кейс, конкурентный контекст, импакт на существующих пользователей, rollout-стратегию и RICE score. | `mvp-analyst` | `base/skills/analyze-mvp.md` |
| `cross-check` | `base:base` | reference or advanced | Проанализировать влияние изменений между backend и iOS. Определить что нужно обновить на другой стороне при изменении API. | `cross-project-analyst` | `base/skills/cross-check.md` |
| `implement-mvp` | `base:base` | reference or advanced | Запустить технический планировщик для MVP-документа. Агент читает продуктовый анализ из docs/mvp/ и формирует TECH_PLAN — технический план реализации с API-контрактом и scope по платформам. После этого можно запускать платформенных архитекторов. | `tech-planner` | `base/skills/implement-mvp.md` |
| `security-check` | `base:base` | primary task entry | Запустить аудит безопасности — проверка на OWASP Top 10, секреты в коде, проблемы с авторизацией. Запускай перед релизом. | `security-auditor` | `base/skills/security-check.md` |
| `write-ui-texts` | `base:base` | reference or advanced | Написать или проверить тексты интерфейса (кнопки, ошибки, пустые состояния, push-уведомления). Агент следит за tone of voice и консистентностью. | `ux-writer` | `base/skills/write-ui-texts.md` |
| `aikit-bootstrap-project` | `public:bootstrap` | primary task entry | Bootstrap an existing project through AIKit discovery, evidence cards, selective RAG and memory candidate review. | - | `docs/public/bootstrap-report-guide.md` |
| `implement-feature` | `profile:python-django` | primary task entry | - | `django-architect`, `django-coder`, `django-tester`, `django-reviewer` | `profiles/python-django/skills/implement-feature.md` |
| `new-app` | `profile:python-django` | reference or advanced | Создать новое Django-приложение с полной структурой (models, admin, serializers, views, urls, tests) | - | `profiles/python-django/skills/new-app.md` |
| `setup-admin` | `profile:python-django` | specialist overlay start | Настроить расширенный Django Admin для существующей модели через admin overlay и canonical Django delivery flow | `django-architect`, `django-admin-expert`, `django-coder`, `django-tester`, `django-reviewer` | `profiles/python-django/skills/setup-admin.md` |
| `add-migration` | `profile:python-fastapi` | reference or advanced | Сгенерировать и применить Alembic-миграцию для изменений в моделях | - | `profiles/python-fastapi/skills/add-migration.md` |
| `implement-feature` | `profile:python-fastapi` | primary task entry | - | `fastapi-architect`, `fastapi-coder`, `fastapi-tester`, `fastapi-reviewer` | `profiles/python-fastapi/skills/implement-feature.md` |
| `new-router` | `profile:python-fastapi` | reference or advanced | Создать новый FastAPI роутер с полной CRUD-структурой (модель, схемы, сервис, роутер, тесты) | - | `profiles/python-fastapi/skills/new-router.md` |
| `add-tests` | `profile:vue-nuxt` | reference or advanced | Написать Vitest и component tests для существующего Vue/Nuxt кода | `vue-tester` | `profiles/vue-nuxt/skills/add-tests.md` |
| `design-implement` | `profile:vue-nuxt` | specialist overlay start | Превратить Figma или design-input в Vue/Nuxt implementation brief и затем провести задачу через design-aware architect/coder flow | `vue-design-bridge`, `vue-architect`, `vue-coder`, `vue-tester`, `vue-reviewer` | `profiles/vue-nuxt/skills/design-implement.md` |
| `design-review` | `profile:vue-nuxt` | specialist overlay start | Проверить Vue/Nuxt реализацию на соответствие UI kit, дизайн-токенам и Figma-макету. | `vue-design-bridge` | `profiles/vue-nuxt/skills/design-review.md` |
| `implement-feature` | `profile:vue-nuxt` | primary task entry | - | `vue-architect`, `vue-coder`, `vue-tester`, `vue-reviewer` | `profiles/vue-nuxt/skills/implement-feature.md` |
| `new-component` | `profile:vue-nuxt` | reference or advanced | Создать Vue-компонент с типизированными props, emits и понятным API для переиспользования | - | `profiles/vue-nuxt/skills/new-component.md` |
| `new-composable` | `profile:vue-nuxt` | reference or advanced | Создать новый composable для Vue/Nuxt с корректной реактивностью, явным API и переиспользованием VueUse | - | `profiles/vue-nuxt/skills/new-composable.md` |
| `new-middleware` | `profile:vue-nuxt` | reference or advanced | Создать новый Nuxt route middleware для auth, redirect или navigation policy | - | `profiles/vue-nuxt/skills/new-middleware.md` |
| `new-page` | `profile:vue-nuxt` | reference or advanced | Создать новую Nuxt page с типизированной загрузкой данных, SEO и базовыми UI-состояниями | - | `profiles/vue-nuxt/skills/new-page.md` |
| `new-plugin` | `profile:vue-nuxt` | reference or advanced | Создать новый Nuxt plugin для app-level интеграции, provide/inject или инициализации зависимости | - | `profiles/vue-nuxt/skills/new-plugin.md` |
| `new-server-route` | `profile:vue-nuxt` | reference or advanced | Создать новый Nitro server route для BFF или proxy-логики с безопасной обработкой запроса и ответа | - | `profiles/vue-nuxt/skills/new-server-route.md` |
| `new-store` | `profile:vue-nuxt` | reference or advanced | Создать Pinia store для состояния фичи: данные, loading/error flags и actions | - | `profiles/vue-nuxt/skills/new-store.md` |
| `audit-prompts` | `pack:ai` | reference or advanced | Аудит всех промптов в проекте. Находит проблемы: неявный формат ответа, необработанные edge cases, противоречия, избыточность. | `prompt-engineer` | `packs/ai/skills/audit-prompts.md` |
| `design-prompt` | `pack:ai` | reference or advanced | Создать или улучшить системный промпт для LLM-интеграции. Агент проводит опрос, пишет промпт по стандарту команды и готовит тест-кейсы. | `prompt-engineer` | `packs/ai/skills/design-prompt.md` |
| `dockerize` | `pack:devops` | reference or advanced | Создать Dockerfile, docker-compose.yml и .dockerignore для проекта. Агент анализирует стек и генерирует оптимальную конфигурацию. | `devops-engineer` | `packs/devops/skills/dockerize.md` |
| `setup-ci` | `pack:devops` | reference or advanced | Создать или улучшить GitLab CI/CD пайплайн. Включает стадии тестирования, сборки Docker-образа и деплоя на staging/production. | `devops-engineer` | `packs/devops/skills/setup-ci.md` |
| `coverage-check` | `pack:quality` | reference or advanced | Проверить покрытие тестами и выявить непокрытые критические модули. Запускает coverage, анализирует результат, предлагает тесты для самых важных пробелов. | `quality-analyst` | `packs/quality/skills/coverage-check.md` |
| `tech-debt` | `pack:quality` | reference or advanced | Аудит технического долга в проекте. Выявляет God Objects, дублирование кода, нарушения архитектурных слоёв, незакрытые TODO. Формирует приоритизированный backlog улучшений. | `quality-analyst` | `packs/quality/skills/tech-debt.md` |

## Orchestrated Agents

| Compatibility alias | Owner | Agents |
| --- | --- | --- |
| `/analyze-mvp` | `base:base` | `mvp-analyst` |
| `/cross-check` | `base:base` | `cross-project-analyst` |
| `/implement-mvp` | `base:base` | `tech-planner` |
| `/security-check` | `base:base` | `security-auditor` |
| `/write-ui-texts` | `base:base` | `ux-writer` |
| `/implement-feature` | `profile:python-django` | `django-architect`, `django-coder`, `django-tester`, `django-reviewer` |
| `/setup-admin` | `profile:python-django` | `django-architect`, `django-admin-expert`, `django-coder`, `django-tester`, `django-reviewer` |
| `/implement-feature` | `profile:python-fastapi` | `fastapi-architect`, `fastapi-coder`, `fastapi-tester`, `fastapi-reviewer` |
| `/add-tests` | `profile:vue-nuxt` | `vue-tester` |
| `/design-implement` | `profile:vue-nuxt` | `vue-design-bridge`, `vue-architect`, `vue-coder`, `vue-tester`, `vue-reviewer` |
| `/design-review` | `profile:vue-nuxt` | `vue-design-bridge` |
| `/implement-feature` | `profile:vue-nuxt` | `vue-architect`, `vue-coder`, `vue-tester`, `vue-reviewer` |
| `/audit-prompts` | `pack:ai` | `prompt-engineer` |
| `/design-prompt` | `pack:ai` | `prompt-engineer` |
| `/dockerize` | `pack:devops` | `devops-engineer` |
| `/setup-ci` | `pack:devops` | `devops-engineer` |
| `/coverage-check` | `pack:quality` | `quality-analyst` |
| `/tech-debt` | `pack:quality` | `quality-analyst` |

> For Codex treat this table as compatibility-only aliases. The supported OpenAI/Codex surface is custom agents plus skills.

## Duplicate Or Shadowed Names

Duplicate names are allowed when a profile owns a domain-specific skill or agent, but they must be visible so users understand which profile owns the implementation.

| Name | Owners |
| --- | --- |
| `implement-feature` | `profile:python-django`, `profile:python-fastapi`, `profile:vue-nuxt` |

## Validation

```bash
/aikit-docs --refresh agents-skills-reference
/aikit-doctor --check validate-agents-skills-reference
/aikit-doctor --check validate-documentation-integrity
```
