# Marketplace

Этот документ генерируется из curated registry layer AIKit.
Он показывает, как packs, presets и adapters выглядят как project-facing distribution surface.

- Registry model: `curated-registry`
- Status: `internal-experimental`

## Featured

- Packs: `quality`, `devops`
- Presets: `frontend-team`, `fullstack-web`
- Adapters: `claude`, `codex`, `glm`

## Packs

| Pack | Version | Compatible profiles | Agents | Skills |
|------|---------|---------------------|--------|--------|
| `ai` | `1.0.0` | `python-fastapi`, `python-django` | `ai-architect`, `prompt-engineer` | `design-prompt`, `audit-prompts` |
| `devops` | `1.0.0` | `python-fastapi`, `python-django`, `vue-nuxt` | `devops-engineer` | `dockerize`, `setup-ci` |
| `quality` | `1.0.0` | `python-fastapi`, `python-django`, `vue-nuxt` | `quality-analyst` | `coverage-check`, `tech-debt` |

## Deprecated Profile Compatibility Archive

Archived profile compatibility remains source-resolvable, but it is not a supported public/default adoption claim.

| Pack | Deprecated compatible profiles |
|------|--------------------------------|
| `devops` | `android-kotlin`, `ios-swiftui` |
| `quality` | `ios-swiftui`, `android-kotlin` |

## Presets

| Preset | Profiles | Packs | Recommended adapter |
|--------|----------|-------|---------------------|
| `backend-api` | `python-fastapi` | `quality`, `devops`, `ai` | `claude` |
| `backend-django` | `python-django` | `quality`, `devops`, `ai` | `claude` |
| `frontend-team` | `vue-nuxt` | `quality`, `devops` | `claude` |
| `fullstack-web` | `vue-nuxt`, `python-fastapi` | `quality`, `devops`, `ai` | `claude` |

## Deprecated Preset Archive

These presets stay in source for compatibility, but they are excluded from featured and default public adoption paths.

| Preset | Profiles | Status | Migration note |
|--------|----------|--------|----------------|
| `mobile-android` | `android-kotlin` | `deprecated` | create a project-specific Android profile before new adoption |
| `mobile-ios` | `ios-swiftui` | `deprecated` | create a project-specific iOS profile before new adoption |

## Runtime Adapters

| Adapter | Runtime | Status | Install | Continuation | Runtime entrypoints | Graph execution |
|---------|---------|--------|---------|--------------|---------------------|-----------------|
| `claude` | `claude` | `active` | — | `no` | `3` | `integrated` |
| `codex` | `codex` | `active` | `workspace-sync` | `yes` | `11` | `exploratory` |
| `glm` | `glm` | `active` | `workspace-sync` | `yes` | `7` | `exploratory` |
| `opencode` | `opencode` | `active` | `workspace-sync` | `yes` | `7` | `exploratory` |

## Publishing Rules

- Only manifests that pass validate-config and generated docs sync are eligible for marketplace listing.
- Experimental adapters may be featured, but must be explicitly labeled by maturity.
- Packs and presets are curated registry entries, not user-uploaded marketplace items.

## Distribution Channels

- `docs-surface` (`documentation`) → Generated markdown and HTML docs inside docs/.
- `workspace-install` (`runtime-install`) → attach/build/install/update scripts for Claude and runtime adapters.
- `artifact-bundles` (`distribution-artifact`) → Built adapter bundles and generated docs artifacts for internal sharing.

## Why this exists

Marketplace layer не делает AIKit публичным app store или live registry прямо сейчас.
Но он даёт curated distribution surface, на который уже можно опираться для docs, install choice и bundle comparison без погружения во внутренние maintainer workflows.
