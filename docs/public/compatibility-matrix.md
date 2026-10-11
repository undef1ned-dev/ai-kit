# Compatibility Matrix

Этот документ генерируется из profile, adapter и preset manifests.
Он показывает, что именно в AIKit уже готово как продуктовая поверхность.

## Runtime Adapters

| Adapter | Runtime | Status | Install | Continuation | Runtime entrypoints | Graph execution | Parallel handoff | Memory path |
|---------|---------|--------|---------|--------------|---------------------|-----------------|------------------|-------------|
| `claude` | `claude` | `active` | `—` | `no` | `3` | `integrated` | `no` | `.claude/memory` |
| `codex` | `codex` | `active` | `workspace-sync` | `yes` | `11` | `exploratory` | `no` | `.aikit/memory` |
| `glm` | `glm` | `active` | `workspace-sync` | `yes` | `7` | `exploratory` | `no` | `.aikit/memory` |
| `opencode` | `opencode` | `active` | `workspace-sync` | `yes` | `7` | `exploratory` | `no` | `.aikit/memory` |

## Profiles

| Profile | Operating class | Direction | Ecosystem | Framework | Domain family | Legacy domain | Modes | Skills | Recommended packs |
|---------|-----------------|-----------|-----------|-----------|---------------|---------------|-------|--------|-------------------|
| `python-django` | `product-project` | `backend` | `python` | `django` | `backend` | `backend-django` | `3` | `3` | `quality`, `devops`, `ai` |
| `python-fastapi` | `product-project` | `backend` | `python` | `fastapi` | `backend` | `backend-fastapi` | `3` | `3` | `quality`, `devops`, `ai` |
| `vue-nuxt` | `product-project` | `frontend` | `javascript-typescript` | `vue-nuxt` | `frontend` | `frontend-web` | `11` | `11` | `quality`, `devops` |

## Presets

| Preset | Profiles | Packs | Recommended adapter |
|--------|----------|-------|---------------------|
| `backend-api` | `python-fastapi` | `quality`, `devops`, `ai` | `claude` |
| `backend-django` | `python-django` | `quality`, `devops`, `ai` | `claude` |
| `frontend-team` | `vue-nuxt` | `quality`, `devops` | `claude` |
| `fullstack-web` | `vue-nuxt`, `python-fastapi` | `quality`, `devops`, `ai` | `claude` |

## Deprecated Preset Archive

These presets remain source-resolvable for compatibility but are not supported public defaults.

| Preset | Profiles | Status | Migration note |
|--------|----------|--------|----------------|
| `mobile-android` | `android-kotlin` | `deprecated` | create a project-specific Android profile before new adoption |
| `mobile-ios` | `ios-swiftui` | `deprecated` | create a project-specific iOS profile before new adoption |
