# Runtime Capability Matrix V2

Phase 30 starts adapter conformance v2 by comparing runtime capabilities across Claude, Codex, GLM and OpenCode. The matrix separates native capability, emulated capability and unsupported behavior so AIKit does not overstate runtime support.

## Capability States

- `native` — the runtime adapter exposes the capability directly through its generated artifacts or entrypoints.
- `emulated` — AIKit can provide the behavior through packaged docs, prompts or local scripts, but the runtime does not expose it as a native surface.
- `unsupported` — the behavior must not be claimed for that runtime.

## Required Capability Families

- `instruction_surface`
- `agent_surface`
- `command_surface`
- `canonical_memory`
- `runtime_tools`
- `continuation`
- `mcp_tool_plane`
- `graph_metadata`

## Runtime Matrix

| Runtime | Instruction | Agents | Commands | Memory | Runtime Tools | Continuation | MCP Tool Plane | Graph Metadata |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Claude | native | native | native | emulated | emulated | unsupported | emulated | native |
| Codex | native | native | emulated | native | native | native | native | native |
| GLM | native | native | emulated | native | native | native | native | native |
| OpenCode | native | native | emulated | native | native | native | native | native |

## Validation

```bash
/aikit-doctor --check validate-runtime-capability-matrix-v2
/aikit-doctor --check validate-runtime-tools-fixtures
/aikit-doctor --check validate-config
```
