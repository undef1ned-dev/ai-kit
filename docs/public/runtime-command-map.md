# Runtime Command Map

- Phase / Epic: `P49` / `P49-E1`
- Status: `completed`
- Source phase: [docs/phase-execution/P49.md](../phase-execution/P49.md)
- Fixture: [docs/fixtures/runtime-command-map-fixtures.json](../fixtures/runtime-command-map-fixtures.json)
- Validator: `/aikit-doctor --check validate-runtime-command-map`
- Scope: local, fixture-backed governance for AIKit.

## Contract

Runtime Command Map defines a local contract for `P49-E1`. The contract is source-backed by markdown, JSON fixtures and a validator, so it can be replayed without scanning arbitrary repositories or requiring live provider access.

This contract must not require live credentials, remote provider mutation, external vector DB dependency, GitHub Pages dependency, live repository requirement or destructive git operation. Any case that needs those inputs is a stop condition and remains blocked until represented by explicit local evidence.

## Fixture Model

The fixture stores a `contract` object and a `runtime_command_items` collection. Every item has an `id`, required fields for the epic acceptance gate and local validator references.

- `claude-command-map`: id=claude-command-map; runtime=claude; install_command=scripts/attach.sh; continue_command=use CLAUDE.md and profile skills; docs=docs/cli-runtime.md
- `codex-command-map`: id=codex-command-map; runtime=codex; install_command=/aikit-runtime-workspace codex; continue_command=.codex/CONTINUE_AIKIT_MAINTAINER.md; command_surface=.codex/commands/*.md including /aikit-runtime-workspace; docs=docs/internal/runtime-provider-handoff.md
- `opencode-command-map`: id=opencode-command-map; runtime=opencode; install_command=/aikit-runtime-workspace opencode; continue_command=CONTINUE_AIKIT_MAINTAINER.md; docs=docs/opencode-runtime-guide.md

Codex command surface now has command-first entrypoints for runtime workspace lifecycle through `/aikit-runtime-workspace`, project bootstrap through `/aikit-bootstrap-project` and maintainer compatibility aliases. `scripts/run-runtime-workspace.py` is the internal runner that resolves presets, delegates install/update, syncs command files and runs bootstrap, so public runtime workspace UX stays on the slash-command path instead of script-first instructions.

## Operating Rules

- Treat fixture rows as the source of truth for local replay and governance checks.
- Keep review-required states explicit before promotion, publication, provider mutation, release promotion or memory promotion.
- Use repair commands and validators from the fixture instead of prose-only acceptance.
- Stop when source evidence cannot be represented safely as sanitized local fixtures.

## Runtime Command Map

Runtime Command Map is complete for `P49-E1` when the fixture, validator and phase-state status agree. The acceptance gate is intentionally local and fixture-backed.

## Validation

```bash
/aikit-doctor --check validate-runtime-command-map
```
