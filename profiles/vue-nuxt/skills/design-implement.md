---
name: "design-implement"
description: Превратить Figma или design-input в Vue/Nuxt implementation brief и затем провести задачу через design-aware architect/coder flow
version: "1.0.0"
profile: "vue-nuxt"
tags: ["vue", "nuxt", "design", "figma", "implementation", "uikit"]
orchestrates: ["vue-design-bridge", "vue-architect", "vue-coder", "vue-tester", "vue-reviewer"]
example_prompt: "/design-implement реализуй страницу уведомлений по https://www.figma.com/file/..."
---

Запусти design-to-code flow для Vue/Nuxt.

`vue-design-bridge` в этом skill выступает как prepend overlay, а не как замена delivery chain. Он обязан собрать `DESIGN_IMPLEMENTATION_BRIEF` и вернуть задачу в canonical `vue-architect -> vue-coder -> vue-tester -> vue-reviewer` spine.

$ARGUMENTS

## Entry Surface Class

`/design-implement` is a `specialist overlay start`.

Use it only when design context is the primary scope of the task. If the request is implementation-first and does not need design-led routing, fall back to `/implement-feature` as the primary task entry.

## Контекст перед реализацией

До кодинга собери source-backed frontend intelligence context:
- Figma-to-code context packet;
- live UI kit scanner output или fixture-backed UI kit manifest;
- component reuse recommendations;
- design/code drift report where implementation already exists.

## Frontend intelligence context

`vue-design-bridge` должен вернуть `DESIGN_IMPLEMENTATION_BRIEF` с:
- provider refs and limitations;
- UI kit reuse candidates;
- component/page/composable/store decomposition;
- token and variant decisions;
- validation gates before implementation.

Implementation must not start until this context exists.

## Static design evidence

Static Figma/provider fixtures are review-required evidence, not live Figma verification.

Only claim live Figma verification when the current runtime actually fetched live context and the evidence packet records that source.

## Phase 33 frontend examples

For stale provider evidence:
- record fixture age, provider source and whether live context was fetched in this run;
- treat stale static evidence as implementation guidance only;
- add a drift note when token or variant decisions cannot be confirmed live;
- state no live Figma claim when the runtime only has static fixtures.

Порядок работы:
1. Если известен target artifact или path, сначала изучи его и связанные `components/`, `composables/`, `stores/`
2. Запусти `vue-design-bridge`, чтобы получить `DESIGN_IMPLEMENTATION_BRIEF`
3. На основе brief передай задачу в `vue-architect`, затем в `vue-coder`, `vue-tester` и `vue-reviewer`
4. Не завершай flow на design-bridge: финальная реализация, тесты и release judgment остаются за canonical spine

`vue-design-bridge` должен:
- прочитать Figma/frame или другой design-source
- найти ближайшие UI kit primitives и variants
- предложить decomposition на `page/components/composables/stores/server-route/middleware/plugin`
- отметить gaps в UI kit до начала кодинга

Итоговый flow должен вернуть:
- implementation brief
- architect plan
- результат реализации
- тестовые и review notes

Используй этот skill, когда задача формулируется как:
- реализовать экран по Figma
- собрать страницу или компонент из макета
- перевести design input в инженерный plan

## Anti-patterns

Не делай:
- implementation before Figma-to-code/frontend intelligence context;
- overlay-only delivery without canonical `architect -> coder -> tester -> reviewer` closeout;
- live Figma claim from static fixtures;
- new UI primitives before reuse recommendation;
- hardcoded tokens without drift/gap note;
- design task that skips component/page decomposition.

Не используй его для простого аудита готовой реализации. Для review оставь `/design-review`.

## Validation gates

Минимум:
```bash
pnpm vitest
pnpm eslint .
```
