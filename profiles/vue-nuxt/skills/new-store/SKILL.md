---
name: "new-store"
description: "Создать Pinia store для состояния фичи: данные, флаги loading/error, actions. Используй, когда состояние нужно разделить между страницами или компонентами."
version: "1.0.0"
profile: "vue-nuxt"
tags: ["vue", "nuxt", "pinia", "state"]
orchestrates: []
example_prompt: "/new-store notifications"
---

Создай новый Pinia store.

Если имя store не указано — запроси его у пользователя.

## Контекст перед реализацией

Перед scaffold проверь:
- existing stores and composables;
- frontend intelligence context for target kind `store`;
- whether state is shared across pages/components or can remain local/composable-owned;
- persistence, SSR and user-session boundaries.

## Декомпозиция

Определи:
- state shape and ownership;
- getters/computed derived state;
- actions for load/update/reset;
- API/composable dependencies;
- tests for pending/error/success and reset behavior.

Перед scaffold:
- изучи существующие `components/`, `composables/`, `stores/` и похожие файлы проекта
- проверь, не решается ли задача через уже существующий composable или через reuse текущего store

Создай файл `stores/<name>.ts`.

Требования:
- setup store через `defineStore`
- типизированное состояние
- явные `pending` / `error`
- actions для загрузки, обновления и очистки состояния
- не дублируй store если сценарий решается обычным composable
- если уместно, используй VueUse для persistence или side effects

## Pinia ownership

Store owns shared durable feature state only.

Use store when:
- multiple pages/components need the same state;
- state needs actions, reset or persistence;
- API lifecycle should be centralized.

Prefer composable/local state when the data is scoped to one component or one page interaction.

## Phase 33 frontend examples

Use this rule to reject store for local-only state when:
- modal open state, selected tab or one-page filters do not need cross-route reuse;
- route state can live in query params plus a composable;
- SSR would risk cross-user state leakage;
- actions would only duplicate local component events.

Create Pinia only when Pinia ownership is durable, shared and testable through actions/reset paths.

## Anti-patterns

Не делай:
- global store for page-local filters;
- state shared across users during SSR;
- actions without error handling and reset path;
- duplicated fetch logic across store and composable;
- persistence without explicit opt-in.

После создания:
1. Покажи публичный API store
2. Объясни когда store лучше store, а когда composable
3. Предложи 2-3 тестовых кейса для него

## Validation gates

Минимум:
```bash
pnpm vitest
pnpm eslint .
```
