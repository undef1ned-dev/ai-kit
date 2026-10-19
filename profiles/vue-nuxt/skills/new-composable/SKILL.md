---
name: "new-composable"
description: "Создать composable для Vue/Nuxt с корректной реактивностью, явным API и переиспользованием VueUse. Используй, когда логику компонента нужно вынести в composable."
argument-hint: "<useName>"
version: "1.0.0"
profile: "vue-nuxt"
tags: ["vue", "nuxt", "composable", "vueuse"]
orchestrates: []
example_prompt: "/new-composable useNotificationsFilters"
---

Создай новый composable для Vue/Nuxt.

Запроси у пользователя:
1. Имя composable
2. Для какой задачи он нужен
3. Какие входы и выходы ожидаются
4. Нужны ли async-запросы, debounce, storage или route sync

## Контекст перед реализацией

Перед scaffold проверь:
- existing composables and stores;
- frontend intelligence context for target kind `composable`;
- VueUse alternatives for debounce, storage, media, async state or browser APIs;
- SSR-safe requirements for browser-only side effects.

## Декомпозиция

Определи:
- public API: inputs, returned refs/computed/actions and error surface;
- reactive ownership: local refs/computed vs store state;
- side effects: watchers, route sync, storage, network, lifecycle cleanup;
- tests: sync behavior, async behavior and cleanup.

Перед scaffold:
- изучи существующие `components/`, `composables/`, `stores/` и похожие файлы проекта
- проверь, есть ли уже похожие patterns, VueUse-ready решения или store-level abstractions

Создай файл `composables/<Name>.ts`.

Требования:
- composable должен иметь понятный контракт: входы, возвращаемые значения, ошибки
- корректная реактивность: `ref`, `computed`, `watch` только там, где они действительно нужны
- сначала проверь, можно ли опереться на VueUse, а не писать утилиты вручную
- если есть client-only side effect, учти SSR-safe guard
- не превращай composable в глобальный store

## Reactivity ownership

Composable owns reusable logic, not durable cross-page feature state.

Use:
- `ref` for local mutable state;
- `computed` for derived state;
- `watch` only for explicit side effects with cleanup;
- Pinia store when state must be shared across routes, sessions or multiple feature surfaces.

## Phase 33 frontend examples

For a composable vs store decision:
- choose composable for route-local filters, derived query params and reusable view logic;
- choose store only for shared durable feature state used across pages/components;
- name watch cleanup, SSR guards and VueUse alternatives;
- explain why reactivity ownership stays local or moves to Pinia.

If state only supports one page interaction, do not create a store.

## Anti-patterns

Не делай:
- hidden module-level mutable state that leaks between users;
- watcher side effects without cleanup;
- browser API access without SSR guard;
- composable that duplicates a store;
- broad API that returns unrelated state.

После создания:
1. Покажи публичный API composable
2. Объясни, почему это composable, а не store
3. Предложи 2-3 тестовых кейса

## Validation gates

Минимум:
```bash
pnpm vitest
pnpm eslint .
```
