# Профили — Structured Summary

Этот документ генерируется из `profile.manifest.json` и `capabilities.json`.
Он дополняет ручную документацию, но не заменяет её.

## Direction Model

Profiles are grouped as `direction -> ecosystem -> framework` while source folders remain flat for installer compatibility.

## Python Django (`python-django`)

- Operating class: `product-project`
- Direction: `backend`
- Ecosystem: `python`
- Framework: `django`
- Domain family: `backend`
- Stack profile: `python-django`
- Legacy domain: `backend-django`
- Default chain: `django-architect -> django-coder -> django-tester -> django-reviewer`
- Core roles: `architect`, `coder`, `tester`, `reviewer`
- Specialized roles: `admin-expert`
- Global roles: `cross-project-analyst`, `release-manager`, `security-auditor`
- Workflow contract: `backend-core-delivery` / `django-drf-admin`
- Path signals: `apps/`, `config/`, `manage.py`
- Keywords: `django`, `drf`, `admin`, `serializer`, `viewset`, `modeladmin`, `celery`
- Рекомендуемые паки: `quality`, `devops`, `ai`
- Рекомендуемые скиллы: `implement-feature`, `new-app`, `setup-admin`
- Primary start: `/implement-feature`
- Overlay starts: `/setup-admin`
- Start contract: Choose one primary start or one bounded overlay start; overlays do not replace the default chain.
- Special surfaces: `api-surface`, `admin`, `drf`

### Recommended Entry Paths

- `new-artifact` → `/new-app`
- `small-patch` → `/implement-feature`
- `feature-work` → `/implement-feature`
- `test-only` → `inspect-chain`
- `review-only` → `inspect-chain`

### Role Aliases

- `admin-expert` → `django-admin-expert`
- `architect` → `django-architect`
- `coder` → `django-coder`
- `reviewer` → `django-reviewer`
- `tester` → `django-tester`

### Capability Modes

- `model-admin`
  Globs: `apps/**/models.py`, `apps/**/models/**/*.py`, `apps/**/admin.py`
  Owned by: `django-coder`, `django-reviewer`, `django-tester`, `django-admin-expert`
  Suggested skills: `setup-admin`, `implement-feature`, `new-app`
  Focus: model design and migrations, admin usability and performance, verbose names and ORM conventions
- `api-layer`
  Globs: `apps/**/views.py`, `apps/**/views/**/*.py`, `apps/**/serializers.py`, `apps/**/serializers/**/*.py`, `apps/**/urls.py`
  Owned by: `django-coder`, `django-reviewer`, `django-tester`
  Suggested skills: `implement-feature`, `new-app`
  Focus: DRF views and serializers, validation and response shape, permission boundaries
- `service-query`
  Globs: `apps/**/services.py`, `apps/**/services/**/*.py`, `apps/**/filters.py`, `apps/**/tasks.py`, `apps/**/tests/**/*.py`
  Owned by: `django-coder`, `django-reviewer`, `django-tester`
  Suggested skills: `implement-feature`, `new-app`
  Focus: business logic placement, query efficiency and filtering, background tasks and test isolation

## Python FastAPI (`python-fastapi`)

- Operating class: `product-project`
- Direction: `backend`
- Ecosystem: `python`
- Framework: `fastapi`
- Domain family: `backend`
- Stack profile: `python-fastapi`
- Legacy domain: `backend-fastapi`
- Default chain: `fastapi-architect -> fastapi-coder -> fastapi-tester -> fastapi-reviewer`
- Core roles: `architect`, `coder`, `tester`, `reviewer`
- Specialized roles: `langgraph-expert`
- Global roles: `cross-project-analyst`, `release-manager`, `security-auditor`
- Workflow contract: `backend-core-delivery` / `fastapi-openapi-service`
- Path signals: `routers/`, `schemas/`, `models/`, `migrations/`, `tests/`, `main.py`
- Keywords: `fastapi`, `pydantic`, `sqlalchemy`, `router`, `schema`, `alembic`, `langgraph`
- Рекомендуемые паки: `quality`, `devops`, `ai`
- Рекомендуемые скиллы: `implement-feature`, `new-router`, `add-migration`
- Primary start: `/implement-feature`
- Overlay starts: —
- Start contract: Choose one primary start or one bounded overlay start; overlays do not replace the default chain.
- Special surfaces: `api-surface`, `openapi`, `langgraph`

### Recommended Entry Paths

- `new-artifact` → `/new-router`
- `small-patch` → `/implement-feature`
- `feature-work` → `/implement-feature`
- `test-only` → `inspect-chain`
- `review-only` → `inspect-chain`

### Role Aliases

- `architect` → `fastapi-architect`
- `coder` → `fastapi-coder`
- `langgraph-expert` → `fastapi-langgraph-expert`
- `reviewer` → `fastapi-reviewer`
- `tester` → `fastapi-tester`

### Capability Modes

- `router-schema`
  Globs: `routers/**/*.py`, `schemas/**/*.py`, `main.py`
  Owned by: `fastapi-coder`, `fastapi-reviewer`, `fastapi-tester`
  Suggested skills: `new-router`, `implement-feature`
  Focus: endpoint contracts and response models, request validation, router registration
- `service-model`
  Globs: `services/**/*.py`, `models/**/*.py`, `core/database.py`, `core/jwt.py`
  Owned by: `fastapi-coder`, `fastapi-reviewer`, `fastapi-tester`
  Suggested skills: `implement-feature`, `add-migration`
  Focus: service-layer business logic, SQLAlchemy 2.0 patterns, auth and persistence boundaries
- `migration-test`
  Globs: `migrations/**/*.py`, `alembic/**/*.py`, `tests/**/*.py`
  Owned by: `fastapi-coder`, `fastapi-reviewer`, `fastapi-tester`
  Suggested skills: `add-migration`, `implement-feature`
  Focus: migration safety, test isolation, coverage of API and service flows

## Vue Nuxt (`vue-nuxt`)

- Operating class: `product-project`
- Direction: `frontend`
- Ecosystem: `javascript-typescript`
- Framework: `vue-nuxt`
- Domain family: `frontend`
- Stack profile: `vue-nuxt`
- Legacy domain: `frontend-web`
- Default chain: `vue-architect -> vue-coder -> vue-tester -> vue-reviewer`
- Core roles: `architect`, `coder`, `tester`, `reviewer`
- Specialized roles: `design-bridge`
- Global roles: `cross-project-analyst`, `release-manager`, `security-auditor`
- Workflow contract: `frontend-core-delivery` / `nuxt-ssr-uikit`
- Path signals: `pages/`, `components/`, `composables/`, `stores/`, `server/api/`, `middleware/`, `plugins/`, `layouts/`, `app.vue`, `nuxt.config.`, `vitest.config.`, `playwright.config.`, `eslint.config.`
- Keywords: `vue`, `nuxt`, `frontend`, `page`, `component`, `composable`, `pinia`, `nitro`, `store`, `middleware`, `plugin`, `layout`, `app shell`, `nuxt config`, `vitest`, `playwright`, `eslint`
- Рекомендуемые паки: `quality`, `devops`
- Рекомендуемые скиллы: `implement-feature`, `add-tests`, `new-page`, `new-component`, `design-review`, `design-implement`
- Primary start: `/implement-feature`
- Overlay starts: `/design-implement`, `/design-review`
- Start contract: Choose one primary start or one bounded overlay start; overlays do not replace the default chain.
- Special surfaces: `figma`, `uikit`, `ssr-app-shell`

### Recommended Entry Paths

- `new-artifact` → `/new-page`
- `small-patch` → `/implement-feature`
- `feature-work` → `/implement-feature`
- `test-only` → `/add-tests`
- `review-only` → `/design-review`

### Role Aliases

- `architect` → `vue-architect`
- `coder` → `vue-coder`
- `design-bridge` → `vue-design-bridge`
- `reviewer` → `vue-reviewer`
- `tester` → `vue-tester`

### Capability Modes

- `page`
  Globs: `pages/**/*.vue`
  Owned by: `vue-coder`, `vue-reviewer`, `vue-tester`
  Suggested skills: `new-page`, `design-implement`, `implement-feature`, `add-tests`
  Focus: SSR and hydration safety, useAsyncData or useFetch strategy, SEO and route-level UX states
- `component`
  Globs: `components/**/*.vue`
  Owned by: `vue-coder`, `vue-reviewer`, `vue-tester`
  Suggested skills: `new-component`, `design-implement`, `implement-feature`, `add-tests`
  Focus: typed props, emits, slots, minimal template logic, reusable component API
- `layout`
  Globs: `layouts/**/*.vue`
  Owned by: `vue-coder`, `vue-reviewer`, `vue-tester`
  Suggested skills: `design-implement`, `implement-feature`, `add-tests`
  Focus: app shell composition, navigation and slot boundaries, global UI state without page coupling
- `app-shell`
  Globs: `app.vue`
  Owned by: `vue-coder`, `vue-reviewer`, `vue-tester`
  Suggested skills: `design-implement`, `implement-feature`, `add-tests`
  Focus: root app composition, global providers and wrappers, startup and hydration safety
- `nuxt-config`
  Globs: `nuxt.config.ts`, `nuxt.config.js`, `nuxt.config.mjs`
  Owned by: `vue-coder`, `vue-reviewer`, `vue-tester`
  Suggested skills: `implement-feature`, `add-tests`
  Focus: Nuxt runtime and module configuration, SSR or build implications, safe environment and public runtime config boundaries
- `tooling-config`
  Globs: `vitest.config.ts`, `vitest.config.js`, `playwright.config.ts`, `playwright.config.js`, `eslint.config.js`, `eslint.config.mjs`, `.eslintrc.js`, `.eslintrc.cjs`
  Owned by: `vue-coder`, `vue-reviewer`, `vue-tester`
  Suggested skills: `implement-feature`, `add-tests`
  Focus: frontend tooling stability, test runner and lint config correctness, environment and path alias consistency
- `composable`
  Globs: `composables/use*.ts`
  Owned by: `vue-coder`, `vue-reviewer`, `vue-tester`
  Suggested skills: `new-composable`, `implement-feature`, `add-tests`
  Focus: reactivity correctness, VueUse reuse, SSR-safe side effects
- `store`
  Globs: `stores/*.ts`
  Owned by: `vue-coder`, `vue-reviewer`, `vue-tester`
  Suggested skills: `new-store`, `implement-feature`, `add-tests`
  Focus: Pinia state ownership, actions and transitions, optimistic updates and persistence
- `server-route`
  Globs: `server/api/**/*.ts`
  Owned by: `vue-coder`, `vue-reviewer`, `vue-tester`
  Suggested skills: `new-server-route`, `implement-feature`, `add-tests`
  Focus: Nitro route patterns, auth and proxy safety, response normalization
- `middleware`
  Globs: `middleware/**/*.ts`
  Owned by: `vue-coder`, `vue-reviewer`, `vue-tester`
  Suggested skills: `new-middleware`, `implement-feature`, `add-tests`
  Focus: route guard boundaries, SSR and client navigation safety, auth and redirect correctness
- `plugin`
  Globs: `plugins/**/*.ts`
  Owned by: `vue-coder`, `vue-reviewer`, `vue-tester`
  Suggested skills: `new-plugin`, `implement-feature`, `add-tests`
  Focus: Nuxt plugin lifecycle, provide and injection safety, client/server scoping
