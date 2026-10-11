# Get Started

Этот документ генерируется из presets и adapter manifests.
Его задача — дать самый короткий путь в AIKit без необходимости сначала читать весь каталог документации.

## Fast Install

Claude production path from the target project:

```bash
git submodule add git@github.com:undef1ned-dev/ai-kit.git .aikit-config
git submodule update --init
bash .aikit-config/scripts/attach.sh --preset frontend-team
```

Runtime workspace path:

```text
/aikit-runtime-workspace codex --preset frontend-team --workspace /tmp/aikit-codex
```

Use `/aikit-install-update inspect --preset frontend-team --adapter codex --json` when you need the install/update plan before writing a workspace.

## One Developer Journey

1. Install preset через attach или runtime workspace flow. Для non-Claude install flow используй `/aikit-runtime-workspace`.
2. Запусти `/aikit-bootstrap-project`.
3. Прочитай `BOOTSTRAP_REPORT` и затем проверь `/aikit-doctor --scope install`.
4. Выбери один рабочий slash command из `docs/public/start-here.md`.
5. Используй `docs/index.html` как generated overview этого пути, а `docs/public/agents-skills-reference.md` открывай только после того, как задача уже понятна.

## Choose Your Path

### 1. Production path for Claude

- Если тебе нужен самый стабильный и production-ready сценарий, начни с `Claude`.
- Выбери подходящий preset и подключи AIKit через `attach.sh`.

### 2. Runtime evaluation path

- Если хочешь попробовать non-Claude runtime, сейчас production-supported adapters: `codex`, `glm`, `opencode`.
- Для них используй `/aikit-runtime-workspace <runtime> --preset <preset> --workspace <path>`; Python scripts остаются internal runner layer.

### 3. Compare runtimes before adopting

- Смотри `docs/public/install-matrix.md` для install surface.
- Смотри `docs/public/runtime-maturity-review.md` для maturity verdict.
- Смотри `docs/public/compatibility-matrix.md` для общей платформенной картины.

### 4. Start from the first command, not from internal systems

- После attach или install первым visible command должен быть `/aikit-bootstrap-project`.
- После `BOOTSTRAP_REPORT` выбери один рабочий slash command из `docs/public/start-here.md`.
- Если хочешь понять, какой путь подходит твоей команде, начни с `docs/public/product-story.md`.
- Там собраны готовые сценарии adoption: production rollout, multi-runtime evaluation, team presets and platform curation.

## What The Install Flow Does

- resolves the selected preset, profiles and packs;
- writes the runtime-facing agents, skills and command files;
- initializes canonical `.aikit/memory/` and runtime mirrors;
- records config version metadata for update checks;
- for non-Claude workspaces, publishes runtime entrypoints, runtime tools and continuation contracts;
- runs bootstrap when the lifecycle command is not explicitly told to skip it.

The install surface should feel short; the generated artifacts stay explicit so operators can inspect what changed.

## Preset Quick Starts

| Preset | Best first step | Claude production | Codex workspace | GLM workspace |
|--------|-----------------|-------------------|-----------------|---------------|
| `backend-api` | FastAPI-focused backend setup with quality, devops, and AI tooling. | `bash .aikit-config/scripts/attach.sh --preset backend-api` | `/aikit-runtime-workspace codex --preset backend-api --workspace /tmp/aikit-codex` | `/aikit-runtime-workspace glm --preset backend-api --workspace /tmp/aikit-glm` |
| `backend-django` | Django backend setup with admin-friendly quality and platform tooling. | `bash .aikit-config/scripts/attach.sh --preset backend-django` | `/aikit-runtime-workspace codex --preset backend-django --workspace /tmp/aikit-codex` | `/aikit-runtime-workspace glm --preset backend-django --workspace /tmp/aikit-glm` |
| `frontend-team` | Vue/Nuxt frontend setup with quality and delivery tooling. | `bash .aikit-config/scripts/attach.sh --preset frontend-team` | `/aikit-runtime-workspace codex --preset frontend-team --workspace /tmp/aikit-codex` | `/aikit-runtime-workspace glm --preset frontend-team --workspace /tmp/aikit-glm` |
| `fullstack-web` | Vue/Nuxt + FastAPI setup for fullstack product teams. | `bash .aikit-config/scripts/attach.sh --preset fullstack-web` | `/aikit-runtime-workspace codex --preset fullstack-web --workspace /tmp/aikit-codex` | `/aikit-runtime-workspace glm --preset fullstack-web --workspace /tmp/aikit-glm` |

## Runtime Adoption Guide

| Runtime | When to choose it | First command |
|---------|-------------------|---------------|
| `claude` | Нужен основной production flow AIKit c slash-командами и attach/update contract. | `bash .aikit-config/scripts/attach.sh --preset frontend-team` |
| `codex` | Нужен production-supported non-Claude runtime с install/update flow и continuation handoff. | `/aikit-runtime-workspace codex --preset frontend-team --workspace /tmp/aikit-codex` |
| `glm` | Нужен production-supported non-Claude runtime с install/update flow и continuation handoff. | `/aikit-runtime-workspace glm --preset frontend-team --workspace /tmp/aikit-glm` |
| `opencode` | Нужен production-supported non-Claude runtime с install/update flow и continuation handoff. | `/aikit-runtime-workspace opencode --preset frontend-team --workspace /tmp/aikit-opencode` |

## Slash Commands You Should See

- `/aikit-bootstrap-project` — first-run discovery command.
- `/implement-feature` — default delivery command for normal work.
- `/design-implement` and `/design-review` — design-scoped overlays.
- `/security-check` — focused follow-up command for security audit work.

## Post-Install Verification

After install, run checks in this order:

1. `/aikit-bootstrap-project` — generate `BOOTSTRAP_REPORT` before implementation.
2. Review selected refs, ignored refs and memory candidates.
3. `/aikit-doctor --scope install` — confirm install preset, bootstrap, doctor and first-task readiness.
4. Start one task command from `docs/public/start-here.md`.

Stop if bootstrap selects unsafe refs, asks for durable memory writes directly or suggests a next command that does not match the actual task.

## Progressive Context Model

AIKit should show lightweight evidence first and let the workflow fetch details only when useful:

- `BOOTSTRAP_REPORT` shows selected refs, ignored refs and evidence-card counts;
- context packs show source refs, trust labels and reasons before deeper reading;
- memory candidates stay review-required until a workflow promotes them;
- agents should prefer command and report surfaces before opening large reference catalogs.

## Runtime Lifecycle Command

- `/aikit-runtime-workspace` — user-facing runtime workspace install/update/bootstrap path.
- Internal scripts such as `scripts/run-runtime-workspace.py`, `scripts/install-adapter-package.py` and `scripts/update-adapter-package.py` remain implementation details for the command.

Profile-specific overlays such as `/setup-admin` stay inside profile references after the task is known; they are not part of the global first-screen command set.

## What To Read Next

- `docs/public/start-here.md` — task-first human entry surface: bootstrap, feature work, design and security work.
- `docs/public/release-center.md` — понять текущую версию, update verdict и release workflow.
- `docs/public/product-story.md` — use-case map: кто и зачем использует AIKit, с какими next steps.
- `docs/index.html` — generated docs-home overview for the same start-working flow.
- `docs/catalog.html` — browse/reference surface после того, как первый task route уже выбран.
- `docs/public/install-matrix.md` — понять install/update surface, distribution commands и update path для runtime adapters.
- `docs/public/runtime-maturity-review.md` — понять, какие runtimes уже production-supported.
- `docs/public/marketplace.md` и `docs/public/publishing-workflow.md` — если хочешь сравнить presets, packs и distribution surfaces без углубления во внутренние maintainer workflows.
