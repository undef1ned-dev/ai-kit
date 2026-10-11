# Product Story

Этот документ генерируется из profile, preset и adapter manifests.
Его задача — связать release/install/catalog/marketplace surfaces в одну понятную продуктовую историю: кто использует AIKit, зачем и какой следующий шаг делать.

## What AIKit Is

- AIKit — это operating layer для инженерных AI workflow, а не просто набор markdown-промптов.
- Система связывает profiles, skills, runtime adapters, presets и memory model в единый reproducible setup.
- Один и тот же core может жить в `Claude`, `Codex`, `GLM`, `OpenCode` и будущих runtime без форков контента.

## Use Cases

### 0. Task-first entry after bootstrap

- Если пользователь начинает с существующего репозитория, первым экраном должен быть `docs/public/start-here.md`.
- Этот путь начинается с `/aikit-bootstrap-project`, объясняет `BOOTSTRAP_REPORT` и предлагает один следующий command по outcome.
- Начать: `docs/public/start-here.md` → `docs/public/bootstrap-report-guide.md` → `docs/public/prompt-cookbook.md`.

### 1. Production rollout inside an existing project

- Выбери preset под команду и подключи AIKit через `attach.sh`.
- Это путь, если тебе нужна минимальная цена входа и готовый production flow с profile routing, skills и memory.
- Начать: `docs/public/get-started.md` → `docs/public/install-matrix.md` → `docs/catalog.html`.

### 2. Multi-runtime adoption without rewriting workflows

- Если команда хочет использовать несколько runtime, AIKit уже поддерживает active non-Claude adapters: `codex`, `glm`, `opencode`.
- Это путь, если тебе важно сохранить core workflows и при этом запускать их в разных инструментах.
- Начать: `docs/public/runtime-maturity-review.md` → `docs/public/install-matrix.md` → `docs/public/compatibility-matrix.md`.

### 3. Team bundle onboarding

- Presets превращают profile + packs в дешёвый onboarding path для конкретной команды.
- Это путь, если ты хочешь быстро развернуть frontend, backend или fullstack сценарий без ручной сборки конфигурации.
- Начать: `docs/public/get-started.md` → `docs/public/profiles-summary.md` → `docs/catalog.html`.

### 4. Compare bundles and distribution surfaces

- Marketplace and publishing surfaces explain which packs, presets and adapters already exist for project adoption.
- Это путь, если тебе нужно сравнить bundle options и понять distribution surface, а не вести внутренний maintainer publishing flow вручную.
- Начать: `docs/public/marketplace.md` → `docs/public/publishing-workflow.md` → `docs/public/install-matrix.md`.

### 5. Continuity value before broader rollout

- AIKit treats continuity value as something to falsify with a memory-on vs memory-off counterfactual before it is marketed as a durable product claim.
- The evaluation path must stay local, deterministic and measurable: source refs, drift detection, outcome delta and review paths come before adoption claims.
- Начать: `docs/internal/continuity-cold-resume-pilot.md` → `docs/internal/memory-off-counterfactual-pilot.md` → `docs/internal/shared-memory-contamination-metrics.md`.

## Which Path To Choose

| If you need... | Start here | Then go to |
|----------------|------------|------------|
| Понять, какую команду запускать после bootstrap | `docs/public/start-here.md` | `docs/public/bootstrap-report-guide.md` |
| Быстро внедрить AIKit в рабочий проект | `docs/public/get-started.md` | `docs/public/install-matrix.md` |
| Сравнить runtime и выбрать не только Claude | `docs/public/runtime-maturity-review.md` | `docs/public/compatibility-matrix.md` |
| Понять профили, агенты и skills под задачу | `docs/catalog.html` | `docs/public/profiles-summary.md` |
| Сравнить presets, packs и adapters как distribution surface | `docs/public/marketplace.md` | `docs/public/publishing-workflow.md` |
| Проверить continuity value перед rollout | `docs/internal/continuity-cold-resume-pilot.md` | `docs/internal/memory-off-counterfactual-pilot.md` |

## Team Presets As Product Entry

| Preset | Best fit | Profiles | Packs | Recommended adapter |
|--------|----------|----------|-------|---------------------|
| `backend-api` | FastAPI-focused backend setup with quality, devops, and AI tooling. | `python-fastapi` | `quality`, `devops`, `ai` | `claude` |
| `backend-django` | Django backend setup with admin-friendly quality and platform tooling. | `python-django` | `quality`, `devops`, `ai` | `claude` |
| `frontend-team` | Vue/Nuxt frontend setup with quality and delivery tooling. | `vue-nuxt` | `quality`, `devops` | `claude` |
| `fullstack-web` | Vue/Nuxt + FastAPI setup for fullstack product teams. | `vue-nuxt`, `python-fastapi` | `quality`, `devops`, `ai` | `claude` |

## Domain Profiles

| Profile | Operating class | Direction | Ecosystem | Framework | Domain family | Legacy domain | Stack profile | Core roles | Recommended skills | Recommended packs | Typical path signals |
|---------|-----------------|-----------|-----------|-----------|---------------|---------------|---------------|------------|--------------------|-------------------|----------------------|
| `python-django` | `product-project` | `backend` | `python` | `django` | `backend` | `backend-django` | `python-django` | `architect`, `coder`, `tester`, `reviewer` | `implement-feature`, `new-app`, `setup-admin` | `quality`, `devops`, `ai` | `apps/`, `config/`, `manage.py` |
| `python-fastapi` | `product-project` | `backend` | `python` | `fastapi` | `backend` | `backend-fastapi` | `python-fastapi` | `architect`, `coder`, `tester`, `reviewer` | `implement-feature`, `new-router`, `add-migration` | `quality`, `devops`, `ai` | `routers/`, `schemas/`, `models/`, `migrations/` |
| `vue-nuxt` | `product-project` | `frontend` | `javascript-typescript` | `vue-nuxt` | `frontend` | `frontend-web` | `vue-nuxt` | `architect`, `coder`, `tester`, `reviewer` | `implement-feature`, `add-tests`, `new-page`, `new-component`, `design-review`, `design-implement` | `quality`, `devops` | `pages/`, `components/`, `composables/`, `stores/` |

## Product Surface Map

- `docs/index.html` — docs portal и рекомендуемые journeys.
- `docs/public/start-here.md` — task-first entry surface поверх bootstrap report.
- `docs/public/get-started.md` — самый короткий путь входа.
- `docs/catalog.html` — browse-слой по агентам, skills и profile coverage.
- `docs/public/release-center.md` — release state платформы.
- `docs/public/install-matrix.md` — install/update surface по runtime.
- `docs/public/compatibility-matrix.md` — платформенная картина по adapters, profiles и presets.
- `docs/public/marketplace.md` и `docs/public/publishing-workflow.md` — distribution surface для presets, packs и adapters.

## Recommended Reading Order

1. `docs/public/product-story.md`
2. `docs/public/start-here.md`
3. `docs/public/get-started.md`
4. `docs/index.html`
5. `docs/catalog.html`
6. Далее — специализированный surface под твой путь: install, runtime maturity, distribution surface или release.
