# AIKit Continuity Workflow

AIKit's continuity workflow is a local workflow for reviewing source-backed memory and recovery evidence before it influences a task.

The workflow shows compact rows first, then lets an operator drill into redacted summaries, source refs, review state and why the evidence surfaced. A row marked `review-required`, stale, blocked or quarantined remains visible without becoming approved truth.

## What It Shows

- source refs for the continuity evidence;
- trust labels and authority boundaries;
- redacted summaries instead of private payloads;
- review-required and quarantine states;
- local recovery hints when evidence cannot be used.

## Safety Boundary

The continuity workflow does not publish private memory internals, raw prompts, full tool outputs, provider payloads, credentials or hosted memory state. It also does not create shared-memory authority by display.

Use the workflow to inspect, challenge and route evidence. Promotion still requires the normal review path and validator-backed evidence.
