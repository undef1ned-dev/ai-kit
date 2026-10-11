# Start Here

This is the human entry surface for AIKit. Start with the task you want to complete, not with the list of agents or internal repository systems.

## One Working Flow

1. Connect or install AIKit for the repository you want to work on.
2. Run `/aikit-bootstrap-project`.
3. Read `BOOTSTRAP_REPORT`.
4. Choose one matching slash command from the task routes below.
5. Let that command activate the correct agent chain and validations.

## First Decision Tree

1. If this is a new or newly connected repository, run `/aikit-bootstrap-project`.
2. Read `BOOTSTRAP_REPORT` using [docs/public/bootstrap-report-guide.md](./bootstrap-report-guide.md).
3. Choose exactly one next action from the task routes below.
4. Run the matching slash command.
5. Validate the result before treating the task as complete.

## Profile Start Model

- A `primary task entry` is the normal first command for delivery work after you know the task.
- A `specialist overlay start` is correct only when the task is explicitly design, admin, planning or phase-execution scoped.
- `/aikit-bootstrap-project` is a no-delivery-chain start: discovery happens before any profile-specific delivery chain is selected.
- Overlay starts stay bounded and do not replace the profile's default chain.
- Profile-specific overlays such as `/setup-admin` appear only after the profile is known; they are not part of the global first-screen command set.

## Slash Commands And Agent Chains

- `/aikit-bootstrap-project` activates discovery only: no delivery chain, just `BOOTSTRAP_REPORT` and the first recommended task prompt.
- `/implement-feature` usually activates `architect -> coder -> tester -> reviewer`.
- `/design-implement` activates a design bridge before the normal delivery chain.
- `/design-review` activates a design specialist for review-first work.
- `/security-check` activates a security-first audit path through `security-auditor`.

You do not need to mention agents directly to start normal work. Pick the right command first; inspect agents only when you need reference detail.

## Task Routes

| User intent | Command | Expected output | Validation guidance |
| --- | --- | --- | --- |
| Connect a project | `/aikit-bootstrap-project` | `BOOTSTRAP_REPORT` with detected project, selected refs, ignored refs, evidence cards, selective RAG state, memory candidates and first task prompt. | Run bootstrap validators and review the report contract before trusting evidence. |
| Implement a feature | `/implement-feature` | Bounded implementation plan, code changes and relevant tests for the selected profile. | Run profile-specific tests plus `/aikit-doctor --check validate-config` when AIKit files change. |
| Implement from design | `/design-implement` | UI implementation tied to supplied design context and project conventions. | Run design diff or frontend checks and keep design assumptions explicit. |
| Review a design | `/design-review` | Findings about feasibility, drift, accessibility and implementation risk. | Keep findings linked to source design or file evidence. |
| Security or secrets check | `/security-check` | Risk-focused review of secrets, auth, dependency and permission boundaries. | Stop on secrets exposure and avoid printing sensitive values. |

## Ambiguous Or Incomplete Starts

- If a request mixes ordinary implementation with optional design or admin signals, start with `/implement-feature`.
- Use `/design-review` only when the task is review-first and a design source exists. If the design source is missing, stop and get the source before using that overlay.
- Use `/design-implement` only when the supplied design is the primary input. If implementation is still the main job and design is secondary context, keep `/implement-feature`.
- If a request drifts into repo-maintainer continuity or internal governance, leave this public router and continue from the relevant internal docs surface instead.
- Do not stack multiple start commands for one task. Choose one primary start and pass extra context inside that request.

## Skill Or Direct Agent

Use the matching slash command first when the task is a normal workflow. That command owns routing, context gathering, validation and stop conditions.

Use a direct agent mention only for advanced debugging, a narrow review, or another known specialist path. Direct agent usage should not be the first screen for a new user.

## What Happens Next

- `BOOTSTRAP_REPORT` explains what AIKit found and what it refused to read.
- The first task prompt is the default next action when the report has no blockers.
- Warnings require review, not blind acceptance.
- Blockers require repair and rerun before implementation.
- Memory candidates stay proposals until the selected workflow closes them through the right review path.

## Reference Only

- `docs/index.html` gives the generated start-working overview when you want the same first-run flow as HTML before opening browse/reference surfaces.
- [docs/public/bootstrap-report-guide.md](./bootstrap-report-guide.md) explains how to read `BOOTSTRAP_REPORT` before picking the next command.
- [docs/public/agents-skills-reference.md](./agents-skills-reference.md) lists agents and skills after you know the task.
- [docs/public/prompt-cookbook.md](./prompt-cookbook.md) gives copyable outcome recipes.
- [docs/catalog.html](../catalog.html) remains the generated browse surface.
- If the work turns into maintainer-only continuity or repository governance, leave this public router and continue from the internal maintainer docs surface.

## Validation

```bash
/aikit-doctor --check validate-human-entry-surface
/aikit-doctor --check validate-documentation-integrity
/aikit-doctor --check validate-product-docs
```
