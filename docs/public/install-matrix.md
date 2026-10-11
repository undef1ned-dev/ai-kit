# Install Matrix

Этот документ генерируется из adapter manifests и preset manifests.
Он показывает, как AIKit устанавливается в разные runtime и какие bundle shortcuts уже доступны команде.

## Fast Install Shape

AIKit keeps the public install surface short and command-first:

1. install a preset or runtime workspace;
2. run `/aikit-bootstrap-project`;
3. verify install readiness with `/aikit-doctor --scope install`;
4. choose one first task command from `docs/public/start-here.md`.

Backing runners remain implementation details. User-facing docs should show the command wrapper first and only explain the backing runner when debugging an install issue.

## Runtime Install Surface

| Adapter | Runtime | Status | Install flow | Update flow | Entrypoint style | Continuation | Runtime entrypoints | Graph execution | Memory path |
|---------|---------|--------|--------------|-------------|------------------|--------------|---------------------|-----------------|-------------|
| `claude` | `claude` | `active` | `—` | `yes` | `slash-commands` | `no` | `3` | `integrated` | `.claude/memory` |
| `codex` | `codex` | `active` | `workspace-sync` | `yes` | `prompt-and-skill-invocation` | `yes` | `11` | `exploratory` | `.aikit/memory` |
| `glm` | `glm` | `active` | `workspace-sync` | `yes` | `prompt-and-runner-invocation` | `yes` | `7` | `exploratory` | `.aikit/memory` |
| `opencode` | `opencode` | `active` | `workspace-sync` | `yes` | `prompt-and-command-presets` | `yes` | `7` | `exploratory` | `.aikit/memory` |

## Team Presets

| Preset | Profiles | Packs | Recommended adapter |
|--------|----------|-------|---------------------|
| `backend-api` | `python-fastapi` | `quality`, `devops`, `ai` | `claude` |
| `backend-django` | `python-django` | `quality`, `devops`, `ai` | `claude` |
| `frontend-team` | `vue-nuxt` | `quality`, `devops` | `claude` |
| `fullstack-web` | `vue-nuxt`, `python-fastapi` | `quality`, `devops`, `ai` | `claude` |

## Deprecated Preset Archive

These presets remain source-resolvable for compatibility, but they are not public/default install choices.

| Preset | Profiles | Status | Migration note |
|--------|----------|--------|----------------|
| `mobile-android` | `android-kotlin` | `deprecated` | create a project-specific Android profile before new adoption |
| `mobile-ios` | `ios-swiftui` | `deprecated` | create a project-specific iOS profile before new adoption |

## Recommended First-Run Path

1. Install preset: `bash .aikit-config/scripts/attach.sh --preset frontend-team`
2. Bootstrap: `/aikit-bootstrap-project`
3. Check install status: `/aikit-doctor --scope install`
4. Choose one first task command from `docs/public/start-here.md`.

Advanced/runtime alternatives stay below this primary path.

## Distribution Plan Commands

- Inspect all commands for a preset: `/aikit-install-update inspect --preset frontend-team`
- Inspect commands for one runtime: `/aikit-install-update inspect --preset frontend-team --adapter codex`
- Machine-readable distribution plan: `/aikit-install-update inspect --preset frontend-team --adapter codex --json`

## What Happened After Install

| Path | Runtime | Purpose |
|------|---------|---------|
| `CLAUDE.md` | `claude` | Combined project instruction surface for Claude Code. |
| `.claude/commands/` | `claude` | Slash-command files generated from selected profiles and packs. |
| `.claude/agents/` | `claude` | Runtime-visible specialist agents. |
| `.claude/.config-version` | `claude` | Installed AIKit version marker for update checks. |
| `.aikit/memory/` | all runtimes | Canonical memory root shared across supported adapters. |
| `.claude/memory/` | `claude` | Claude mirror of canonical memory. |
| `.aikit/runtime-entrypoints.json` | non-Claude | Machine-readable launcher surface for runtime workspaces. |
| `.aikit/runtime-tools.json` | non-Claude | Internal tool registry exposed to the installed runtime. |
| `.aikit/runtime-continuation-contract.md` | non-Claude | Continuation rules for resumed runtime flows. |
| `.codex/commands/` | `codex` | Codex command mirror; global prompt sync may require permission to write `~/.codex`. |
| `~/.codex/prompts` | `codex` | Optional global prompt alias side effect when Codex command sync is approved. |

Users run slash commands. Python scripts are diagnostics, CI and internal runner implementation details.

## Post-Install Verification

After install, verify in this order:

1. `/aikit-bootstrap-project`
2. read `BOOTSTRAP_REPORT` and confirm selected/ignored refs
3. `/aikit-doctor --scope install`
4. choose exactly one next task command from `docs/public/start-here.md`

## Support Quality Gate

`ADAPTER_SUPPORT_SCORECARD` is the local support quality gate for Claude Code, Codex, GLM and OpenCode. It ranks install/update, runtime workspace recovery, command recovery and public docs parity evidence without adding new runtime capability claims.

When support evidence points to adapter drift, use the existing repair commands and rerun Doctor before starting task work.

## Troubleshooting

Use this recovery path before opening reference catalogs:

```text
/aikit-doctor --scope install
/aikit-install-update inspect --preset frontend-team --adapter codex
/aikit-runtime-workspace codex --preset frontend-team --workspace /tmp/aikit-codex --operation update
/aikit-doctor --scope install
```

The first command checks readiness, the update command is the recommended repair command for stale Codex runtime workspaces and the final Doctor run is the rerun command.

## Already Installed? Update Path

| Runtime | Update command | Verify after update |
|---------|----------------|---------------------|
| `claude` | `bash .aikit-config/scripts/update.sh` | `/aikit-doctor --scope install` |
| `codex` | `/aikit-runtime-workspace codex --preset frontend-team --workspace /tmp/aikit-codex --operation update` | `/aikit-doctor --check validate-adapter-fixtures` |
| `glm` | `/aikit-runtime-workspace glm --preset frontend-team --workspace /tmp/aikit-glm --operation update` | `/aikit-doctor --check validate-adapter-fixtures` |
| `opencode` | `/aikit-runtime-workspace opencode --preset frontend-team --workspace /tmp/aikit-opencode --operation update` | `/aikit-doctor --check validate-adapter-fixtures` |

## Reading the Matrix

- `status` показывает maturity адаптера как runtime surface.
- `install flow` показывает, есть ли у runtime собственный install contract, а не только package builder.
- `update flow` показывает, может ли runtime безопасно пересинхронизировать уже установленный workspace.
- `runtime entrypoints` показывает, насколько адаптер умеет публиковать actionable launcher surface.
- `graph execution` показывает maturity packaged DAG metadata для orchestration recipes.
