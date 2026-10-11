# GLM Runtime Guide

This guide documents practical GLM usage for AIKit.

It is source-backed guidance, not proof that a live GLM terminal session was started.

## Start

Use the runtime workspace lifecycle command:

```text
/aikit-runtime-workspace glm --preset backend-django --workspace /tmp/aikit-glm
```

The slash command uses internal build/install/update/bootstrap scripts under the hood; those scripts are not the primary user-facing runtime path.

The installed workspace should contain:
- `.glm/AIKIT.md`;
- `.glm/CONTINUE_AIKIT_MAINTAINER.md`;
- `.glm/entrypoints.json`;
- `.aikit/runtime-entrypoints.json`;
- `.aikit/runtime-continuation-contract.md`;
- `.aikit/runtime-tools.json`;
- `.aikit/memory/`.

## Continue

Use `.glm/CONTINUE_AIKIT_MAINTAINER.md` as the continuation prompt.

The runtime agent should read:
- `.glm/AIKIT.md`;
- packaged maintainer agent surface in `.aikit/agents/`;
- `.aikit/runtime-operating-protocol.md`;
- `.aikit/runtime-continuation-contract.md`;
- `.aikit/runtime-tools.json`;
- `.aikit/memory/INDEX.md`.

## Provider Handoff

For provider-backed tasks, read [docs/runtime-provider-handoff.md](../internal/runtime-provider-handoff.md) before implementation.

GLM should treat provider export packets as review-required context:
- use Figma packets as frontend intelligence evidence;
- use GitHub packets as repository/backend context evidence;
- keep selected evidence refs visible in the task journal;
- run provider export and ingestion validators before memory promotion.

Static provider packets are not live provider access and are not live runtime verification.

## Validate

Run:

```bash
/aikit-doctor --check validate-adapter-conformance-v2
/aikit-doctor --check validate-adapter-continuation
/aikit-doctor --check validate-runtime-install-update-smoke
/aikit-doctor --check validate-runtime-packet-compatibility
/aikit-doctor --check validate-provider-export-packets
/aikit-doctor --check validate-provider-evidence-ingestion
```

## Troubleshoot

If the continuation launcher is missing, rebuild the adapter package and reinstall the workspace.

If `.aikit/runtime-tools.json` is missing, do not select internal AIKit validators from the runtime. Rebuild and rerun adapter validation first.

If runtime packet fields are missing, run `/aikit-doctor --check validate-runtime-packet-compatibility` before attempting live usage.

## Limitations

- GLM support is validated through source-backed manifests, package artifacts and fixtures.
- This guide does not claim a live GLM terminal session was started.
- Provider export packets are static review-required evidence unless a live GLM runtime supplies fresh provider context.
- Runtime-specific behavior must stay inside `adapters/glm/` unless a shared core contract intentionally changes.
