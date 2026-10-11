# Bootstrap Report Guide

Use this guide after `/aikit-bootstrap-project`.

`BOOTSTRAP_REPORT` is a task-first handoff. It is not a raw scanner dump and not durable memory.

## What To Confirm First

1. `detected_project` matches the repository you intended to inspect.
2. `selected_refs` look like safe local evidence for the next task.
3. `ignored_refs` show that secrets, dependencies, build output, traversal paths and outside-root refs stayed out of scope.
4. `validation` has no blockers.
5. `first_task_prompt` matches the task you want to do next.

## How To Read Each Section

| Report block | What it means | What to do |
| --- | --- | --- |
| `detected_project` | AIKit picked a project shape, profile and preset hints. | Confirm the profile feels right before continuing. |
| `selected_refs` | Safe local evidence AIKit may use next. | Review the scope and treat it as bounded context, not as the whole repository. |
| `ignored_refs` | Boundaries the scanner respected on purpose. | Treat this as safety evidence, not as missing work. |
| `evidence_cards` | Review-required summaries built from selected refs. | Use them as guidance, then inspect the cited files if the task is high-risk. |
| `selective_rag` | Local knowledge hydration state. | Continue only if it is based on approved local sources. |
| `memory_candidates` | Proposed memory, not accepted memory. | Approve, reject or defer them later through the normal workflow. |
| `validation` | Bootstrap health and blockers. | Fix blockers first; warnings require review. |
| `first_task_prompt` | The default next action. | Run one matching task command after the report looks safe. |

## Trust Labels

- `canonical`: directly inspectable local files or validated generated outputs.
- `review-required`: summaries and evidence cards that still need human judgment.
- `inspect-only`: boundaries or references that explain scope but should not be promoted into memory as facts.
- `session-continuation`: temporary handoff context for the current run, not durable product truth.

## Stop Conditions

- selected evidence includes secrets, dependency folders, build output, traversal or outside-root refs;
- bootstrap asks for durable memory write directly;
- validation is blocked;
- the suggested next step does not match the task you actually want to do.

## Next Step

After `BOOTSTRAP_REPORT`, go back to [docs/public/start-here.md](./start-here.md) and choose one matching task command.

## Validation

```bash
/aikit-doctor --check validate-bootstrap-report-human-contract
/aikit-doctor --check validate-human-entry-surface
/aikit-doctor --check validate-documentation-integrity
```
