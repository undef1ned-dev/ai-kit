# Prompt Cookbook 2.0

This cookbook is organized by outcome. It is not a raw command dump and it does not ask users to manually orchestrate internal scripts as the primary workflow.

Start with [docs/public/start-here.md](./start-here.md), use the bootstrap report guide at [docs/public/bootstrap-report-guide.md](./bootstrap-report-guide.md), then copy one recipe that matches the result you want.

## Recipe Format

Every recipe includes:

- when to use it;
- prompt template;
- expected result;
- validation gates;
- stop conditions.

## Recipes

### Bootstrap Existing Project

When to use it: connect AIKit to a local repository and get one first task prompt.

Prompt template:

```text
/aikit-bootstrap-project
```

Expected result: `BOOTSTRAP_REPORT` with detected project, selected refs, ignored refs, evidence cards, selective RAG status, memory candidates, validation and first task prompt.

Validation gates:

- `/aikit-doctor --check validate-bootstrap-scanner`
- `/aikit-doctor --check validate-bootstrap-report-human-contract`

Stop conditions:

- selected evidence includes secrets, dependency folders, build output, traversal or outside-root refs;
- bootstrap writes durable memory directly;
- report asks for live credentials or external provider mutation.

Good prompt:

```text
/aikit-bootstrap-project
After the report, recommend one next command for implementing the first safe task.
```

Bad prompt:

```text
Scan my whole computer and memorize the project forever.
```

### Implement Feature

When to use it: change product behavior in an existing project.

Prompt template:

```text
/implement-feature Add invoice export for completed orders.
Use the bootstrap report evidence and keep the diff bounded to the owning profile.
```

Expected result: implementation plan, code changes, relevant tests and validation summary.

Validation gates:

- profile test command;
- changed-file lint or typecheck when available;
- `/aikit-doctor --check validate-config` when AIKit source files change.

Stop conditions:

- task needs missing product requirements;
- implementation would cross unrelated ownership boundaries;
- destructive git operation is required.

### Create Page Component Router App

When to use it: add a new frontend page/component, FastAPI router, Django app, Android screen or iOS view.

Prompt template:

```text
/implement-feature Create a notifications page with filters and empty state.
Target path: pages/notifications.vue.
```

Expected result: new artifact in the owning profile, wired into local conventions and covered by focused validation.

Validation gates:

- profile-specific build or test command;
- route/component import check;
- local docs or bootstrap evidence if project conventions changed.

Stop conditions:

- no target path or owning profile can be inferred;
- request mixes unrelated page, backend and release work without acceptance criteria.

### Review Code

When to use it: find bugs, regressions, missing tests or unsafe assumptions before merging.

Prompt template:

```text
Review the current diff for behavioral bugs and missing validation.
Focus on changed files and directly coupled code paths.
```

Expected result: findings first, with file/line references and severity.

Validation gates:

- reproduce relevant failing checks where possible;
- keep non-blocking style notes out of the main findings.

Stop conditions:

- review scope lacks a diff, file list or target branch;
- requested review needs secrets or production-only data.

### Design Review

When to use it: evaluate implementation feasibility, accessibility or visual drift before coding.

Prompt template:

```text
/design-review Review this Figma flow against the current frontend conventions.
Call out feasibility, accessibility, reused components and missing states.
```

Expected result: design findings, implementation risks and required follow-up states.

Validation gates:

- link findings to design nodes or local component evidence;
- note missing responsive, loading, empty and error states.

Stop conditions:

- design source is missing;
- review would require guessing hidden product requirements.

### Design Implementation

When to use it: implement a provided design node or screen.

Prompt template:

```text
/design-implement Implement the notification settings screen from the supplied design context.
Match existing components and run frontend validation.
```

Expected result: production UI code with design fidelity, responsive behavior and validation summary.

Validation gates:

- browser or screenshot check for visual regressions where applicable;
- component tests or build check;
- accessibility and text-fit review.

Stop conditions:

- design assets or required node context are unavailable;
- implementation would create a parallel design system.

### Security Check

When to use it: inspect sensitive boundaries before release or after auth/config changes.

Prompt template:

```text
/security-check Review the auth and environment variable changes in this diff.
Do not print secret values.
```

Expected result: risk-ranked findings and concrete remediation.

Validation gates:

- check secret handling, permissions, auth flow and dependency risk;
- verify no sensitive values are included in the report.

Stop conditions:

- request asks to expose, decode or persist secrets;
- live production access is required.

## Ambiguous Or Incomplete Requests

- `/implement-feature` is the fallback when the request mixes delivery with optional overlay signals such as design or admin context.
- If the design source is missing, stop and get the design source before `/design-review` or `/design-implement`.
- If the request mixes broader implementation with optional admin work, keep `/implement-feature` as the start instead of `/setup-admin`.
- Do not stack multiple start commands in one opening prompt. Choose the primary route, then attach supporting context.

## Validation

```bash
/aikit-doctor --check validate-prompt-cookbook-v2
/aikit-doctor --check validate-documentation-integrity
/aikit-doctor --check validate-product-docs
```
