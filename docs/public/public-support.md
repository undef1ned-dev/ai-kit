# Public Support

Use GitHub Issues for public AIKit feedback. Keep reports reproducible and do not include secrets.

## Before Opening An Issue

Run the public checks that match the failure:

```text
/aikit-doctor --scope install
/aikit-install-update inspect --preset frontend-team
```

For runtime workspace issues, include the recovery command shape, not private files:

```text
/aikit-runtime-workspace codex --preset frontend-team --workspace /tmp/aikit-codex --operation update
```

## What To Include

- AIKit version from `docs/public/release-center.md`;
- runtime: Claude Code, Codex, GLM or OpenCode;
- command that failed;
- source report: `DOCTOR_REPORT`, `COMMAND_RECOVERY_REPORT` or `RUNTIME_WORKSPACE_REPORT`;
- report status;
- blocker names;
- expected result;
- actual result;
- redacted evidence paths;
- recovery attempted.

Do not include secrets, tokens, private repository content, proprietary source snippets or personal credentials.

## Support Feedback

If a maintainer asks for follow-up, rerun `/aikit-doctor --scope install`, rerun the failed command, update the redacted evidence and include the public docs page that looked stale.

## Known Issue Freshness

Known issues are short public notes based on reproducible support signals. Candidate review status remains `candidate-review-only`; it does not publish a release or promise a date.

Freshness notes may ask you to rerun Doctor, rerun the failed command and refresh redacted evidence. No public SLA is promised.

## Troubleshooting Path

1. Run `/aikit-doctor --scope install`.
2. Use the recommended repair command from `DOCTOR_REPORT`.
3. Check [Doctor](../../docs-site/troubleshooting/doctor.mdx) and [Recovery](../../docs-site/troubleshooting/recovery.mdx).
4. Open a GitHub issue when the same failure remains reproducible.

For stale Codex runtime workspaces:

- Recommended repair command: `/aikit-runtime-workspace codex --preset frontend-team --workspace /tmp/aikit-codex --operation update`
- Rerun command: `/aikit-doctor --scope install`

## Stop Conditions

Stop before implementation work when Doctor still reports blockers after the repair command, or when recovery would require credentials, provider mutation, production deploy or DNS cutover.
