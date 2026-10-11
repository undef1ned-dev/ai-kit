# Support Intake

Use this shape when opening a public AIKit issue after recovery remains reproducible.

## Before Reporting

Run the public recovery path first:

```text
/aikit-doctor --scope install
```

If Doctor names a repair command, run it and then rerun Doctor.

For stale Codex runtime workspaces:

```text
/aikit-runtime-workspace codex --preset frontend-team --workspace /tmp/aikit-codex --operation update
/aikit-doctor --scope install
```

## Required Fields

- AIKit version from `docs/public/release-center.md`
- Runtime: Claude Code, Codex, GLM or OpenCode
- Command that failed
- Source report: `DOCTOR_REPORT`, `COMMAND_RECOVERY_REPORT` or `RUNTIME_WORKSPACE_REPORT`
- Report status
- Blocker names
- Expected result
- Actual result
- Redacted evidence paths
- Recovery attempted

## Evidence Rules

Include short summaries, command names, report status, blocker names and redacted local paths.

Do not include secrets, tokens, private repository content, proprietary source snippets, raw provider responses, personal credentials, production deploy requests or DNS cutover requests.

## Support Feedback

If a maintainer asks for follow-up, rerun `/aikit-doctor --scope install`, rerun the failed command, update the redacted evidence and include the public docs page that looked stale.

## Known Issue Freshness

Use known issue notes only for public, reproducible behavior. Freshness notes may ask for a rerun and refreshed redacted evidence. No public SLA is promised.
