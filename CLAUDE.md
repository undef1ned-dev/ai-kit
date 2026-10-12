# AIKit — Базовые правила команды

## Контекст
Мы разрабатываем продукты AIKit. Репозитории объединены в общую группу.
Этот файл — базовый слой правил, общий для всех проектов.
Профиль проекта (vue-nuxt, python-fastapi и т.д.) расширяет эти правила.

---

## Язык

- **Код, имена файлов, комментарии** — English
- **Коммиты, MR описания, задачи** — Russian
- **Общение с Клодом** — Russian

---

## Git-workflow

### Ветки — скилл `git-branch` (Conventional Branch)
```
main                  — стабильная версия, изменения только через PR/MR с ревью
develop               — интеграционная ветка (если используется)
<type>/<description>  — feat/, fix/, hotfix/, release/, chore/
                        например feat/oauth-login, fix/issue-42-empty-list-crash, release/v1.4.0
```

### Коммиты — скилл `git-commit` (Conventional Commits)
```
feat(auth): добавлена авторизация через OAuth
fix: исправлено падение при пустом списке
build(deps): обновлены зависимости
```

- Формат `<type>[(scope)][!]: <description>`, описание на русском
- Никакого соавторства: без `Co-Authored-By` и приписок `Generated with ...`
- Одна задача — один коммит
- Не коммитить сломанный код в develop/main

### Merge Requests
- Описание: что сделано и зачем (не как)
- Минимальный diff — не рефакторить попутно
- Указывать связанный issue: `Closes #42`

---

## Принципы работы с кодом

- **Минимум изменений** — трогаем только то, что нужно для задачи
- **Не рефакторить попутно** — отдельная задача, отдельный MR
- **Без over-engineering** — не добавлять абстракции под гипотетические требования
- **Без force unwrap** — явная обработка опционалов
- **Без магических чисел** — именованные константы
- Код должен быть читаем без комментариев; комментарии — только там, где логика неочевидна

---

## Безопасность

- Никаких секретов, токенов, паролей в коде или конфигах
- Секреты — только через переменные окружения или защищённые хранилища
- Не коммитить `.env`-файлы с реальными значениями

---

## Взаимодействие с Claude

- Перед изменением файла — прочитай его
- Не создавай новые файлы если можно отредактировать существующий
- Не добавляй docstrings/комментарии к коду, который не менялся
- Перед destructive-операциями (удаление файлов, reset, force push) — спросить подтверждение
- Если задача неясна — уточни, не угадывай

---

## Развитие агентной системы

Базовые скиллы доступны в любом проекте:

### Создание и расширение
- `/create-agent` — создать нового агента через структурированное интервью (6 фаз)
- `/create-skill` — создать новый скилл (`/команду`) через интервью (4 фазы)
- `/improve-aikit` — развивать сам репозиторий AIKit через специализированного maintainer-агента

### Анализ и планирование
- `/analyze-mvp` — проанализировать идею фичи перед разработкой
- `/implement-mvp` — перевести MVP-документ в технический план по платформам (API-контракт, scope, порядок реализации)

### Git
- `git-branch` — именование веток (применяется автоматически)
- `git-commit` — формат коммитов, без соавторства (применяется автоматически)

### Релиз и качество
- `/security-check` — аудит безопасности (OWASP, секреты, авторизация)

### Тексты и дизайн
- `/write-ui-texts` — написать или проверить тексты интерфейса (кнопки, ошибки, пустые состояния)

### Кросс-проектная координация
- `/cross-check` — анализ влияния изменений между backend и iOS

### Оркестрация
- `/implement-feature <задача>` — реализовать фичу цепочкой агентов профиля: architect → coder → tester + reviewer; агентов и команды проверки берёт из `.aikit/profiles.json`. `--tdd` — сначала падающие тесты, `--worktree` — работа в отдельном git worktree
- `/fix-bug <баг>` — воспроизвести баг, написать тест, который его ловит, исправить и проверить
- `/check-feature <фича>` — запустить приложение командой `run` профиля и проверить фичу в браузере или запросами
- `/workflow <задача>` — интерактивный визард: определяет тип задачи, строит цепочку агентов, ведёт шаг за шагом

### Память проекта
- `/capture-memory` — зафиксировать командную память после задачи: решения, паттерны, коррекции агентов в `.aikit/memory/` (общая для команды, хранится в git; личное — во встроенной памяти runtime)
- `/memory-status` — показать, что накоплено в `.aikit/memory/`, и открытые memory-PR
- `/optimize-memory` — сжать INDEX, объединить дубли, убрать устаревшее (запускать при предупреждении от `/memory-status`)

Новые агенты и скиллы добавляются в `claude-config` через PR/MR в основной репозиторий.

---

# Vue Nuxt Profile

Профиль для frontend-разработки на Vue 3 + Nuxt 3.
Расширяет базовые правила команды из `base/CLAUDE.md`.

---

## Стек

- **Node.js 20+**
- **Vue 3** + **Nuxt 3/4-ready** — SSR, SSG, file-based routing, server routes
- **TypeScript** — обязателен для нового кода
- **Composition API** + **`<script setup lang="ts">`**
- **Pinia** — глобальное клиентское состояние
- **VueUse** — composables и утилиты, не писать велосипед
- **useFetch / useAsyncData** — загрузка данных в Nuxt
- **Nitro server routes** — BFF/edge-логика при необходимости
- **Vitest** + **@vue/test-utils** — unit/component тесты
- **Playwright** — E2E и визуальная проверка
- **Figma MCP** — сверка реализации с макетами и UI kit контекст
- **ESLint + Prettier** — стиль и форматирование

---

## Архитектура

### Типичная структура проекта
```text
app.vue
pages/
  index.vue
  account/
    index.vue
components/
  base/
  feature/
layouts/
composables/
  useAuth.ts
  useFilters.ts
stores/
  auth.ts
  notifications.ts
middleware/
plugins/
utils/
types/
nuxt.config.ts
server/
  api/
    notifications/
      index.get.ts
      [id].patch.ts
  utils/
tests/
  unit/
  components/
  e2e/
```

### Слои
```text
Page → Feature Components → Composables / Store → API Client / useFetch → server/api (если нужен BFF)
```

### Правила распределения логики
- `pages/` — композиция экрана и SEO, без тяжёлой бизнес-логики
- `components/` — переиспользуемый UI и feature-части экрана
- `layouts/` — app shell, общая навигация, shared wrappers, не конкретная page-логика
- `app.vue` — корневой composition layer приложения, глобальные wrappers и startup UI
- `nuxt.config.*` — runtime config, модули, aliases, SSR/build switches, integration boundaries
- `composables/` — локальная reusable-логика, работа с query params, form flows, VueUse
- `stores/` — cross-page состояние, кэш, optimistic update, auth/session
- `middleware/` — route guards, auth gates, redirects, navigation policies
- `plugins/` — интеграции Nuxt app level, provide/inject, client/server scoped setup
- `server/api/` — прокси, агрегация API, скрытие токенов и BFF-логика

### Динамическая экспертиза агентов
- Если задача затрагивает `pages/**/*.vue` — агент обязан включить режим page/Nuxt: SSR, `useAsyncData`, SEO, route params, hydration
- Если задача затрагивает `components/**/*.vue` — агент обязан включить режим component API: props, emits, slots, `data-test`, переиспользуемость
- Если задача затрагивает design review, Figma или UI kit — агент обязан включить режим design bridge: reuse существующих компонентов, tokens, states, visual consistency
- Если задача затрагивает `layouts/**/*.vue` — агент обязан включить режим layout/app shell: shared navigation, slot boundaries, global UI composition
- Если задача затрагивает `app.vue` — агент обязан включить режим root app shell: providers, wrappers, startup behavior, hydration safety
- Если задача затрагивает `nuxt.config.*` — агент обязан включить режим Nuxt config: modules, runtime config, aliases, SSR/build impact
- Если задача затрагивает `composables/use*.ts` — агент обязан включить режим composable: reactivity, VueUse reuse, watch/computed hygiene, SSR-safe side effects
- Если задача затрагивает `stores/*.ts` — агент обязан включить режим Pinia: ownership of state, actions, optimistic updates, persistence
- Если задача затрагивает `middleware/**/*.ts` — агент обязан включить режим route middleware: redirect loops, auth boundaries, SSR/client navigation safety
- Если задача затрагивает `plugins/**/*.ts` — агент обязан включить режим Nuxt plugin: runtime injection, client/server scoping, side-effect hygiene
- Если задача затрагивает `server/api/**/*.ts` — агент обязан включить режим Nitro/BFF: auth propagation, request validation, proxy safety, response shaping
- Если задача затрагивает `vitest/playwright/eslint config` — агент обязан включить режим tooling config: test stability, aliases, environment consistency

Агент не должен требовать отдельного выбора "узкого специалиста", если тип файлов уже делает нужный режим очевидным.

---

## Правила кода

### Обязательно
- Только `script setup` + TypeScript в новом Vue-коде
- Props и emits типизированы через `defineProps` / `defineEmits`
- Сложную UI-логику выносить в composables, не в шаблон
- Для глобального состояния использовать Pinia, не event bus
- Перед написанием своего composable проверять есть ли решение во VueUse
- Для page data использовать `useAsyncData` / `useFetch` с явным key
- Ошибки и loading-состояния должны быть явными
- Переиспользуемые компоненты должны иметь понятный API: props, slots, emits

### Запрещено
- Options API в новом коде
- `any` без реальной причины
- Хардкод API URL внутри компонентов
- Логика авторизации прямо в page/component, если это должно жить в store/composable
- Дублирование fetch-логики в нескольких местах
- Прямые обращения к `window` / `document` без проверки client-only контекста

### Nuxt-специфика
```vue
<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const { data, pending, error, refresh } = await useAsyncData(
  () => `profile:${route.params.id}`,
  () => $fetch(`/api/profile/${route.params.id}`)
)
</script>
```

- Для SSR-safe кода учитывать `import.meta.client` / `import.meta.server`
- SEO задавать через `useSeoMeta`
- Query params синхронизировать аккуратно, без циклических watch
- Для форм предпочитать schema-first подход (например Zod), если он уже есть в проекте

---

## Именование

| Что | Правило | Пример |
|-----|---------|--------|
| Page | kebab-case по роуту | `pages/orders/[id].vue` |
| Component | PascalCase | `OrderCard.vue`, `NotificationsPanel.vue` |
| Composable | `use<Name>` | `useAuth.ts`, `usePropertyFilters.ts` |
| Store | `<name>.ts` + `use<Name>Store` | `auth.ts`, `useAuthStore` |
| Type | PascalCase | `NotificationItem`, `ProfileResponse` |
| Server route | REST + method suffix | `server/api/orders/index.get.ts` |

---

## Тесты

- **Vitest** — composables, stores, utils, component logic
- **@vue/test-utils** — props, emits, slots, conditional rendering
- **Playwright** — happy path, формы, навигация, SSR/CSR flows
- Тестировать поведение, а не внутреннюю реализацию

```ts
import { describe, it, expect } from "vitest"
import { setActivePinia, createPinia } from "pinia"
import { useAuthStore } from "~/stores/auth"

describe("auth store", () => {
  it("stores session after login", async () => {
    setActivePinia(createPinia())
    const store = useAuthStore()

    store.setSession({ token: "token", user: { id: 1, name: "Ada" } })

    expect(store.isAuthenticated).toBe(true)
    expect(store.user?.name).toBe("Ada")
  })
})
```

---

## Доступные скиллы

- `/new-page` — создать новую Nuxt page с загрузкой данных и SEO
- `/new-component` — создать Vue-компонент с типизированными props/slots/emits
- `/new-composable` — создать composable с корректной реактивностью и использованием VueUse
- `/new-middleware` — создать route middleware для auth, redirect или navigation policy
- `/new-plugin` — создать Nuxt plugin для интеграции app-level зависимостей
- `/new-server-route` — создать Nitro server route для BFF/proxy-логики
- `/new-store` — создать Pinia store для состояния фичи
- `/add-tests` — написать Vitest/VTU тесты для существующего кода
- `/design-review` — проверить реализацию на соответствие UI kit, токенам и Figma
- `/design-implement` — превратить Figma/макет в implementation brief и затем пройти design-aware delivery flow
