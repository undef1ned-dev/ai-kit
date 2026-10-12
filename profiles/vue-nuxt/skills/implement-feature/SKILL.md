---
name: "implement-feature"
template: "implement-feature"
profile: "vue-nuxt"
tags: ["vue", "nuxt", "implementation"]
orchestrates: ["vue-architect", "vue-coder", "vue-tester", "vue-reviewer"]
example_prompt: "/implement-feature страница уведомлений с фильтрами и mark-as-read"
tvar_PLATFORM: Vue/Nuxt
tvar_PREFIX: vue
tvar_TESTER_DESC: "Vitest + @vue/test-utils тесты, при необходимости E2E через Playwright"
tvar_TAGS: '"vue", "nuxt", "implementation"'
tvar_ORCHESTRATES: '"vue-architect", "vue-coder", "vue-tester", "vue-reviewer"'
tvar_EXAMPLE_PROMPT: "/implement-feature страница уведомлений с фильтрами и mark-as-read"
---

## Контекст перед реализацией

## Entry Surface Class

`/implement-feature` is the `primary task entry` for normal Vue/Nuxt delivery.

Use it when the task is implementation-first and should go through the canonical `vue-architect -> vue-coder -> vue-tester -> vue-reviewer` chain. If design context is the primary scope, escalate into `/design-implement` instead of treating it like an ordinary feature start.

До проектирования собери frontend intelligence context:
- изучи существующие `components/`, `composables/`, `stores/` и похожие файлы проекта;
- проверь frontend task workflow route, UI kit manifest and component reuse recommendations;
- если задача содержит backend/API/provider refs, сохрани их как source-backed context, not implementation truth.

## Декомпозиция

ARCHITECT_PLAN должен разделить feature на:
- page shell and route ownership;
- feature components and component APIs;
- composables for reusable logic;
- Pinia store only for shared durable feature state;
- server/api or backend dependency if needed;
- tests and validation gates.

[STEP1_CONTEXT]
- Прочитай PRODUCT.md и текущие `pages/`, `components/`, `composables/`, `stores/`
- Спроектируй: page, feature components, composables, stores, server/api если нужен BFF

## UI kit reuse

Перед кодом:
- check existing primitives, variants and feature components;
- document reuse decisions and UI kit gaps;
- avoid new tokens/components unless context proves a gap.

## Phase 33 frontend examples

For a cross-stack API contract feature, ARCHITECT_PLAN must name:
- backend response fields, status codes and empty/error states the page consumes;
- page/component/composable split, with page owning data loading and visual components receiving typed props;
- optimistic action failure behavior and rollback;
- validation gates for frontend workflow plus the backend/API contract evidence used.

Do not hide API contract decisions inside a component fetch. Keep the page shell and composable boundaries explicit.

## Anti-patterns

Не принимай результат, если:
- coding starts before frontend intelligence context;
- page/component/store boundaries are mixed;
- UI kit reuse was skipped;
- SSR/hydration risks are not named;
- tests do not cover key UI states.

[REPORT_EXTRAS]
### Routes
<список страниц и маршрутов>

### State
<какие composables/stores добавлены>

[NEXT_STEPS]
pnpm vitest
pnpm eslint .
pnpm dev

## Validation gates

Минимум:
```bash
pnpm vitest
pnpm eslint .
```
