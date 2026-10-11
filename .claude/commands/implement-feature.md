---
name: "implement-feature"
description: Реализовать Vue/Nuxt-фичу через цепочку агентов: архитектор → кодер → тестировщик + ревьюер
version: "1.0.0"
profile: "vue-nuxt"
tags: ["vue", "nuxt", "implementation"]
orchestrates: ["vue-architect", "vue-coder", "vue-tester", "vue-reviewer"]
example_prompt: "/implement-feature страница уведомлений с фильтрами и mark-as-read"
---

Реализуй фичу через цепочку специализированных Vue/Nuxt-агентов.

Фича: $ARGUMENTS

## Шаг 1 — Архитектура (vue-architect)

Используй агент vue-architect:
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
- Выведи ARCHITECT_PLAN

Дождись результата.

## Шаг 2 — Реализация (vue-coder)

Используй агент vue-coder с ARCHITECT_PLAN:
- Выведи CODER_RESULT

Дождись результата.

## Шаг 3 — Параллельно: тесты и ревью

Запусти одновременно:
- vue-tester — Vitest + @vue/test-utils тесты, при необходимости E2E через Playwright
- vue-reviewer — проверка на соответствие стандартам

## Итог

```
## Фича реализована: <название>
### Routes
<список страниц и маршрутов>

### State
<какие composables/stores добавлены>

### Созданные файлы
<список>

### Тесты
<список>

### Замечания ревью
<если есть — что нужно исправить>

### Следующие шаги
pnpm vitest
pnpm eslint .
pnpm dev

## Validation gates

Минимум:
```bash
pnpm vitest
pnpm eslint .
```
```

Если на любом шаге агент вернул вопросы или неоднозначности — остановись и уточни у пользователя перед продолжением.
