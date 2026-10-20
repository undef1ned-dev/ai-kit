---
name: "design-review"
description: "Проверить Vue/Nuxt-реализацию на соответствие UI kit, дизайн-токенам и Figma-макету. Используй, когда нужно сверить готовый UI с дизайном."
argument-hint: "<файл и ссылка на макет>"
version: "1.0.0"
profile: "vue-nuxt"
tags: ["vue", "nuxt", "design", "figma", "design-system", "uikit"]
orchestrates: ["vue-design-bridge"]
example_prompt: "/design-review pages/account/index.vue и https://www.figma.com/file/..."
---

Запусти агент `vue-design-bridge` для проверки соответствия UI kit и дизайн-системе.

Если задача не про аудит, а про реализацию нового экрана или компонента по Figma/макету, используй `/implement-feature` со ссылкой на макет, а не этот skill.

$ARGUMENTS

## Entry Surface Class

`/design-review` is a `specialist overlay start`.

Use it only when the task is explicitly review-first and design-scoped. If the request is implementation-first, use `/implement-feature` with the mockup link instead.

## Контекст перед реализацией

Перед review собери:
- UI kit scanner output;
- component reuse recommendations;
- drift report if code exists;
- Figma/provider refs with limitations.

## Frontend intelligence context

Review должен ссылаться на frontend intelligence context:
- selected UI kit refs;
- ignored reuse candidates and reason;
- token/component drift findings;
- owner-routed follow-up actions.

## Static design evidence

Static design fixtures are review-required evidence and cannot prove live Figma state.

If no live Figma context is available, say that review is source-backed/static and avoid live verification claims.

Агент должен:
1. Найти источник токенов, базовых компонентов и UI kit в проекте
2. Проверить, что страница или компонент не используют лишний хардкод вместо системных primitives
3. Если указан Figma URL или frame — сверить реализацию с макетом через Figma MCP
4. Предложить переиспользование существующих компонентов и нужные расширения UI kit
5. Явно отметить gaps, которые стоит вынести в будущий frontend intelligence / UI kit слой

Примеры:
- `/design-review pages/account/index.vue` — проверить страницу на соответствие системе
- `/design-review components/profile/ProfileCard.vue` — проверить компонент и tokens
- `/design-review https://www.figma.com/file/...` — сверить будущую или текущую реализацию с макетом

## Phase 33 frontend examples

For token drift finding, include:
- the expected token family and actual implementation token or hardcoded value;
- component reuse finding with selected or ignored reuse candidate;
- owner-routed action for UI kit, feature component or page code;
- drift baseline reference before claiming a regression.

If the drift report lacks baseline context, mark the finding as source-limited instead of overstating certainty.

## Anti-patterns

Не делай:
- design review without source refs;
- live Figma verification claim from static fixture;
- token drift finding without owner/action;
- ignoring component reuse recommendations;
- review that only comments on visuals and skips implementation contract.
