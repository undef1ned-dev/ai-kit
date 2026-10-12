---
name: "new-page"
description: "Создать Nuxt-страницу с типизированной загрузкой данных, SEO и состояниями loading, error, empty. Используй, когда нужна новая страница или роут."
version: "1.0.0"
profile: "vue-nuxt"
tags: ["vue", "nuxt", "page", "scaffold"]
orchestrates: []
example_prompt: "/new-page account/notifications"
---

Создай новую Nuxt page.

Если путь страницы не указан — запроси его у пользователя.

## Контекст перед реализацией

Перед scaffold собери frontend intelligence context:
- изучи существующие `components/`, `composables/`, `stores/` и похожие файлы проекта;
- проверь UI kit manifest, component reuse recommendations and frontend task workflow context gate;
- проверь SSR data source, auth needs, route params and layout constraints.

## Декомпозиция

Раздели страницу на:
- page shell: route, SEO, data loading, state selection;
- feature component: heavy UI blocks and interaction surfaces;
- composables: reusable data/query/filter logic;
- stores: shared feature state only when page-local state is insufficient;
- tests: page smoke, component behavior and key states.

SSR/hydration boundary обязателен: browser-only APIs must be guarded and client-only effects must not run during server rendering.

Создай:
- `pages/<route>.vue`

Перед scaffold:
- проверь, какие `components/`, `composables/`, `stores/` и UI kit artifacts уже есть в проекте

Требования:
- `<script setup lang=\"ts\">`
- `useSeoMeta()` для title
- явные loading / error / empty / success состояния
- `useAsyncData()` или `useFetch()` в зависимости от сценария
- вынеси тяжёлую UI-часть в локальный feature component если экран получается большим
- учитывай SSR-safe поведение

## UI kit reuse

Перед созданием новых primitives:
- выбери существующие UI kit components, variants and tokens already present in the project;
- если нужен новый component, explain why existing primitive is insufficient;
- keep loading/error/empty/success states visually consistent with existing page patterns.

## Phase 33 frontend examples

For an SSR provider evidence join:
- record provider refs as review-required context, not implementation truth;
- map provider fields through the backend/API contract before page state;
- keep `useAsyncData()` or `useFetch()` SSR-safe and provide fallback for missing provider fields;
- render loading, error, empty and success states with UI kit reuse before creating new primitives.

If provider evidence and API contract disagree, stop and ask for a contract decision before scaffolding.

## Anti-patterns

Не делай:
- page that hardcodes tokens or bypasses UI kit primitives;
- client-only API access during SSR;
- data fetching hidden inside visual components;
- route page without loading, error, empty and success states;
- giant page component when feature components are warranted.

После создания:
1. Покажи путь страницы
2. Объясни какие данные грузятся на сервере
3. Подскажи какие composables/store стоит добавить следующим шагом

## Validation gates

Минимум:
```bash
pnpm vitest
pnpm eslint .
```
