---
name: "new-component"
description: Создать Vue-компонент с типизированными props, emits и понятным API для переиспользования
version: "1.0.0"
profile: "vue-nuxt"
tags: ["vue", "nuxt", "component", "scaffold"]
orchestrates: []
example_prompt: "/new-component NotificationsPanel"
---

Создай новый Vue-компонент.

Запроси у пользователя:
1. Имя компонента
2. Где он живёт: `components/base/`, `components/feature/` или внутри конкретной фичи
3. Какие props нужны
4. Нужны ли emits или slots

## Контекст перед реализацией

Перед scaffold собери frontend intelligence context:
- изучи существующие `components/`, `composables/`, `stores/` и похожие файлы проекта;
- проверь UI kit manifest, component reuse recommendations, existing base/feature components and token names;
- уточни component API: props, emits, slots, accessibility and test selectors.

## Декомпозиция

Раздели component contract на:
- public API: typed props, emits and slots;
- rendering states: default, loading, empty, error, disabled where relevant;
- composition: UI kit primitives first, local markup only when necessary;
- interaction: minimal local state and emitted events;
- tests: API and key state behavior.

Перед scaffold:
- изучи существующие `components/`, `composables/`, `stores/` и похожие файлы проекта
- посмотри, нет ли уже подходящего primitive, variant или близкого feature component в проекте

Требования:
- `script setup lang=\"ts\"`
- типизированные props и emits
- предсказуемый API компонента
- минимум логики в шаблоне
- `data-test` атрибуты для ключевых интеракций если компонент интерактивный

## UI kit reuse

Перед созданием нового component:
- сначала проверь existing primitive, variant or feature component;
- reuse existing tokens and spacing scale;
- if extending UI kit, document the gap and intended owner.

## Phase 33 frontend examples

For token and variant review, document the component API before coding:
- props, emits and slots that are public and stable;
- selected UI kit primitive or variant and why it fits;
- token names used for color, spacing and typography;
- unsupported variant or slot ownership gaps that justify a new component.

If token drift appears, report it as a component API concern and avoid hardcoded fallback styles.

## Anti-patterns

Не делай:
- component with implicit API or untyped emits;
- business workflow logic in template;
- hardcoded colors/spacing where UI kit token exists;
- component that duplicates an existing primitive;
- interactive component without stable test selectors.

После создания кратко опиши:
1. API компонента
2. Где его лучше использовать
3. Нужен ли к нему отдельный тест

## Validation gates

Минимум:
```bash
pnpm vitest
pnpm eslint .
```
