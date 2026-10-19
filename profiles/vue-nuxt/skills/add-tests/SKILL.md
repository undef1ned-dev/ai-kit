---
name: "add-tests"
description: "Написать Vitest и component-тесты (@vue/test-utils) для существующего Vue/Nuxt-кода. Используй, когда пользователь просит покрыть тестами компонент, composable или store."
argument-hint: "<файлы для тестов>"
version: "1.0.0"
profile: "vue-nuxt"
tags: ["vue", "nuxt", "testing"]
orchestrates: ["vue-tester"]
example_prompt: "/add-tests pages/account/index.vue и stores/auth.ts"
---

Запусти агент `vue-tester` для написания тестов.

$ARGUMENTS

Агент должен:
1. Найти существующие компоненты, stores, composables или pages
2. Определить критические сценарии: success / loading / error / emits
3. Написать Vitest и @vue/test-utils тесты
4. Если полезно и доступен dev-сервер — предложить E2E проверку через Playwright
