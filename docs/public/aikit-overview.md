# AIKit

AIKit is a repository of reusable agent workflows, profile rules, runtime adapters, retrieval tooling, and memory contracts for engineering AI work.

The core idea is simple:
- a human talks to Claude, Codex, GLM, or OpenCode in a familiar CLI;
- the runtime selects the right profile, context, tools, and workflow;
- AIKit keeps the task grounded with documents, retrieval, and memory instead of ad-hoc prompting.

## What You Get

- `core + adapters` architecture for multiple AI runtimes
- domain profiles for `vue-nuxt`, `python-fastapi`, `python-django`
- packaged agents, skills, presets, and workflow manifests
- CLI-native runtime orchestration via `scripts/run-agent-task.py`
- explainable retrieval / RAG with context packs
- canonical runtime-neutral memory in `.aikit/memory/`

## Profiles

<!-- GENERATED:PROFILES_TABLE:START -->
| Профиль | Direction | Ecosystem | Framework | Domain family | Primary start | Overlay starts | Default chain |
|---------|-----------|-----------|-----------|---------------|---------------|----------------|---------------|
| `python-django` | `backend` | `python` | `django` | `backend` | `/implement-feature` | `/setup-admin` | `django-architect -> django-coder -> django-tester -> django-reviewer` |
| `python-fastapi` | `backend` | `python` | `fastapi` | `backend` | `/implement-feature` | — | `fastapi-architect -> fastapi-coder -> fastapi-tester -> fastapi-reviewer` |
| `vue-nuxt` | `frontend` | `javascript-typescript` | `vue-nuxt` | `frontend` | `/implement-feature` | `/design-implement`, `/design-review` | `vue-architect -> vue-coder -> vue-tester -> vue-reviewer` |
<!-- GENERATED:PROFILES_TABLE:END -->

<!-- GENERATED:PROFILES_SUMMARY:START -->
### `python-django` — Python Django
- Operating class: `product-project`
- Direction: `backend`
- Ecosystem: `python`
- Framework: `django`
- Domain family: `backend`
- Stack profile: `python-django`
- Legacy domain: `backend-django`
- Default chain: `django-architect -> django-coder -> django-tester -> django-reviewer`
- Core roles: `architect`, `coder`, `tester`, `reviewer`
- Capability modes: `model-admin`, `api-layer`, `service-query`
- Path signals: `apps/`, `config/`, `manage.py`
- Рекомендуемые паки: `quality`, `devops`, `ai`
- Рекомендуемые скиллы: `implement-feature`, `new-app`, `setup-admin`
- Primary start: `/implement-feature`
- Overlay starts: `/setup-admin`
- Start contract: Choose one primary start or one bounded overlay start; overlays do not replace the default chain.
- Recommended entry paths: `new-artifact` → `/new-app`, `small-patch` → `/implement-feature`, `feature-work` → `/implement-feature`, `test-only` → `inspect-chain`, `review-only` → `inspect-chain`

### `python-fastapi` — Python FastAPI
- Operating class: `product-project`
- Direction: `backend`
- Ecosystem: `python`
- Framework: `fastapi`
- Domain family: `backend`
- Stack profile: `python-fastapi`
- Legacy domain: `backend-fastapi`
- Default chain: `fastapi-architect -> fastapi-coder -> fastapi-tester -> fastapi-reviewer`
- Core roles: `architect`, `coder`, `tester`, `reviewer`
- Capability modes: `router-schema`, `service-model`, `migration-test`
- Path signals: `routers/`, `schemas/`, `models/`, `migrations/`, `tests/`, `main.py`
- Рекомендуемые паки: `quality`, `devops`, `ai`
- Рекомендуемые скиллы: `implement-feature`, `new-router`, `add-migration`
- Primary start: `/implement-feature`
- Overlay starts: —
- Start contract: Choose one primary start or one bounded overlay start; overlays do not replace the default chain.
- Recommended entry paths: `new-artifact` → `/new-router`, `small-patch` → `/implement-feature`, `feature-work` → `/implement-feature`, `test-only` → `inspect-chain`, `review-only` → `inspect-chain`

### `vue-nuxt` — Vue Nuxt
- Operating class: `product-project`
- Direction: `frontend`
- Ecosystem: `javascript-typescript`
- Framework: `vue-nuxt`
- Domain family: `frontend`
- Stack profile: `vue-nuxt`
- Legacy domain: `frontend-web`
- Default chain: `vue-architect -> vue-coder -> vue-tester -> vue-reviewer`
- Core roles: `architect`, `coder`, `tester`, `reviewer`
- Capability modes: `page`, `component`, `layout`, `app-shell`, `nuxt-config`, `tooling-config`, `composable`, `store`, `server-route`, `middleware`, `plugin`
- Path signals: `pages/`, `components/`, `composables/`, `stores/`, `server/api/`, `middleware/`, `plugins/`, `layouts/`, `app.vue`, `nuxt.config.`, `vitest.config.`, `playwright.config.`, `eslint.config.`
- Рекомендуемые паки: `quality`, `devops`
- Рекомендуемые скиллы: `implement-feature`, `add-tests`, `new-page`, `new-component`, `design-review`, `design-implement`
- Primary start: `/implement-feature`
- Overlay starts: `/design-implement`, `/design-review`
- Start contract: Choose one primary start or one bounded overlay start; overlays do not replace the default chain.
- Recommended entry paths: `new-artifact` → `/new-page`, `small-patch` → `/implement-feature`, `feature-work` → `/implement-feature`, `test-only` → `/add-tests`, `review-only` → `/design-review`
<!-- GENERATED:PROFILES_SUMMARY:END -->

## Start Here

### 1. Choose the way you want to work

| Path | Use when | First step |
| --- | --- | --- |
| `Claude Code` | You want the most established attach-based flow inside an existing project. | `bash .claude-config/scripts/attach.sh --preset frontend-team` |
| `Codex / GLM / OpenCode` | You want a workspace-sync install with runtime entrypoints and continuation bundles. | `/aikit-runtime-workspace codex --preset frontend-team --workspace /tmp/aikit-codex` |

Release and update state lives in [docs/release-center.md](./release-center.md). Use it to check the current version, update verdict and release workflow before updating installed workspaces.
Distribution commands live in [docs/install-matrix.md](./install-matrix.md). Use `/aikit-runtime-workspace codex --preset frontend-team --workspace /tmp/aikit-codex --dry-run` when you need a machine-readable install/update plan for a preset.

### 2. Choose what you want to install

- `profile` if you need one domain, for example `vue-nuxt`
- `preset` if you want a curated team bundle, for example `frontend-team` or `fullstack-web`
- `pack` if you want extra capabilities like `quality`, `devops`, or `ai`

### 3. Run the matching command

Claude attach flow:

```bash
git submodule add git@github.com:your-org/aikit.git .claude-config
git submodule update --init
bash .claude-config/scripts/attach.sh --preset frontend-team
```

Codex runtime workspace:

```text
/aikit-runtime-workspace codex --preset frontend-team --workspace /tmp/aikit-codex
```

GLM runtime workspace:

```text
/aikit-runtime-workspace glm --preset frontend-team --workspace /tmp/aikit-glm
```

OpenCode runtime workspace:

```text
/aikit-runtime-workspace opencode --preset frontend-team --workspace /tmp/aikit-opencode
```

### 4. Start working from a task, not from internal scripts

The intended UX is:

1. You describe the task in your model CLI.
2. The runtime picks the profile, retrieval context, and workflow.
3. AIKit prepares the handoff packet, validation steps, and next actions.
4. Memory and knowledge are updated as part of the flow, not as a manual side quest.

You can inspect the first CLI runtime entrypoint directly:

```bash
/aikit-run-task \
  --task "Добавить composable для фильтров уведомлений" \
  --path composables/useNotificationsFilters.ts \
  --json
```

## How The System Works

### Core model

```text
Task from user
  -> profile routing
  -> retrieval / context pack
  -> workflow plan
  -> runtime-specific handoff
  -> validation / finalize steps
  -> memory + knowledge updates
```

### Adapters

AIKit keeps one shared core and publishes runtime-specific surfaces through adapters:

- `claude` for attach/update flows
- `codex` for Codex CLI / desktop workspace installs
- `glm` for GLM Terminal / agent runtime installs
- `opencode` for OpenCode workspace installs

Installed non-Claude workspaces receive:
- `.aikit/runtime-entrypoints.json`
- `.aikit/runtime-tools.json`
- `.aikit/runtime-operating-protocol.md`
- `.aikit/runtime-continuation-contract.md`

### Agents and skills

- agents hold role-specific behavior like architecture, coding, review, testing, memory, or platform maintenance
- skills are shorter entry paths for common tasks
- workflows define how these pieces connect for a concrete task or recipe

The fastest visual overview lives in [docs/catalog.html](../catalog.html).

## RAG And Retrieval

AIKit does not rely only on the current chat.

It builds a local knowledge layer so the runtime can fetch relevant context before implementation starts.

### What goes into RAG

- documentation from `docs/*.md`
- structured manifests and workflow metadata
- canonical memory from `.aikit/memory/`
- generated knowledge store artifacts
- future domain contracts such as UI kit, API surface, and design-aware knowledge

### What retrieval does

`scripts/build-context-pack.py` turns:
- task text
- profile
- optional target path
- optional target kind or intent

into an explainable context pack with:
- selected documents and chunks
- memory facts and constraints
- relevant contracts and suggested artifacts
- reasons why each source was selected

This is “RAG” in the practical AIKit sense: not generic embeddings-first search, but a profile-aware retrieval layer that gives the next agent a useful, auditable briefing.

After `MR-E1`, this layer is no longer treated only as hidden infrastructure.
AIKit now models knowledge actions as an explicit runtime tool family:
- `query` for retrieval/bootstrap,
- `memory` for durable `.aikit/memory/` capture,
- `maintenance` for knowledge-store refresh,
- `governance` for drift/freshness checks.

After `MR-E2`, the same runtime tool plane also understands `mcp-tool`:
- runtime-native provider tools like Figma or GitHub can be described in the same registry;
- they keep `provider` and `runtime_binding` instead of pretending to be shell commands;
- this makes local scripts and future MCP integrations part of one explainable contract.

After `MR-E3`, the runtime can also explain *why* a task goes through retrieval, memory capture, local validation, or provider actions.
That policy now surfaces in runtime packets as `tool_family_routing`.

Runtime packets also surface `routing_guidance`, so low-confidence profile matches can be reviewed with explicit sanity checks, override candidates and ready rerun commands instead of staying buried in raw routing metadata.

After `MR-E4`, runtime packets also keep `runtime_observation_log`, so execution artifacts can feed future memory and knowledge enrichment instead of disappearing into raw status fields.

After `MR-E5`, runtime packets can also expose `external_knowledge_bridge`, so a CLI agent can explain how canonical repo knowledge should be combined with live Figma/GitHub provider context before external actions happen.

Runtime packets now also expose `memory_lifecycle`, so agents can see when canonical task memory has grown enough to justify a controlled `tasks/archive` batch instead of endlessly appending new active task logs.

Read more:
- [docs/retrieval-context-builder.md](../internal/retrieval-context-builder.md)
- [docs/knowledge-model.md](../internal/knowledge-model.md)
- [docs/knowledge-storage.md](../internal/knowledge-storage.md)
- [docs/mcp-rag-roadmap.md](../internal/mcp-rag-roadmap.md)

## MEMORY In AIKit

Memory is the continuity layer between tasks and sessions.

### Canonical rule

- source of truth: `.aikit/memory/`
- Claude compatibility mirror: `.claude/memory/`

### What memory is for

- decisions that should survive beyond one chat
- reusable implementation patterns
- corrections after mistakes
- task history and feature notes
- constraints that future agents should respect

### Why it matters

Without memory, each new session starts from partial context.
With memory, the runtime can surface prior decisions and operating constraints inside retrieval and handoff flows.

Read more:
- [docs/canonical-memory-model.md](../internal/canonical-memory-model.md)
- [docs/knowledge-governance.md](../internal/knowledge-governance.md)

## Repository Map

```text
adapters/   runtime-specific packaging and entrypoints
base/       shared agents, skills, memory templates, and baseline rules
profiles/   domain-specific prompts, agents, skills, and workflows
presets/    curated team bundles
packs/      optional capability add-ons
docs/       product surface, contracts, roadmap, and generated references
scripts/    validators, generators, retrieval, runtime, packaging, and install utilities
knowledge/  retrieval policy, manifests, and generated knowledge artifacts
```

Docs taxonomy and audience split live in docs surface map and [docs/docs-surface-manifest.json](../docs-surface-manifest.json).

## Most Useful Commands

Validate repository config:

```bash
/aikit-doctor --check validate-config
```

Validate adapter fixtures:

```bash
/aikit-doctor --check validate-adapter-fixtures
```

Build local knowledge store:

```bash
/aikit-knowledge-refresh --rebuild
```

Check knowledge drift:

```bash
/aikit-knowledge-refresh --check-drift
```

Build a context pack:

```bash
/aikit-knowledge-refresh --context-pack \
  --profile vue-nuxt \
  --task "Измени composable useAuth для refresh token flow" \
  --path composables/useAuth.ts \
  --json
```

Run the CLI runtime entrypoint:

```bash
/aikit-run-task \
  --task "Продолжить design-to-code workflow" \
  --profile vue-nuxt \
  --execute-policy safe \
  --json
```

Build an adapter package:

```bash
/aikit-install-update build codex --profile vue-nuxt
```

## Recommended Reading Order

If you want the shortest onboarding path:

1. [docs/index.html](../index.html)
2. [docs/catalog.html](../catalog.html)
3. [docs/get-started.md](./get-started.md)
4. [docs/cli-runtime.md](../internal/cli-runtime.md)

If you want the platform model:

1. [docs/multi-runtime-architecture.md](../internal/multi-runtime-architecture.md)
2. [docs/manifest-spec.md](./manifest-spec.md)
3. [docs/adapter-runtime-execution.md](./adapter-runtime-execution.md)

If you want the knowledge layer:

1. [docs/knowledge-model.md](../internal/knowledge-model.md)
2. [docs/retrieval-context-builder.md](../internal/retrieval-context-builder.md)
3. [docs/canonical-memory-model.md](../internal/canonical-memory-model.md)

## Product Surface

- [docs/index.html](../index.html) — onboarding portal and “how AIKit works” surface
- [docs/catalog.html](../catalog.html) — interactive catalog of profiles, agents, and skills
- docs surface map — docs surface map by audience and ownership
- [docs/mcp-rag-roadmap.md](../internal/mcp-rag-roadmap.md) — next product roadmap for MCP-aware knowledge, memory, and tool convergence
- [docs/product-story.md](./product-story.md) — scenario narrative for rollout and platform adoption
- [docs/install-matrix.md](./install-matrix.md) — install paths for runtimes and presets
- [docs/runtime-maturity-review.md](./runtime-maturity-review.md) — current maturity verdict

## Current Positioning

AIKit is already useful as:
- a shared agent and skill repository
- a multi-runtime adapter base
- a retrieval-aware engineering workflow layer
- a continuity system with runtime-neutral memory

The next maturity steps are about making the runtime even more autonomous, not about inventing the foundation from scratch.
