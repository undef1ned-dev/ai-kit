# Adapter Conformance V2

`P14-E1` expands adapter conformance for Claude, Codex, GLM and OpenCode.

Conformance v2 is source-backed. It validates manifests, entrypoints, continuation surfaces, runtime tools and install/update expectations. It does not claim that a live runtime session was started.

## Required Fields

Each conformance fixture declares:
- adapter id;
- expected status;
- runtime label;
- continuation requirement;
- runtime tools requirement;
- install/update model;
- required scripts;
- required entrypoints;
- required generated artifacts;
- limitations;
- production claim scope.

## Runtime Groups

### Claude

Claude uses core workspace attach/update:
- `attach_script`;
- `update_script`;
- direct `CLAUDE.md` and `.claude/` surfaces.

Claude does not use the packaged `runtime-tools-registry` path as its primary conformance surface.

### Codex, GLM and OpenCode

Packaged runtimes use workspace-sync:
- `install_script`;
- `update_script`;
- continuation prompt;
- `.aikit/runtime-entrypoints.json`;
- `.aikit/runtime-continuation-contract.md`;
- `.aikit/runtime-tools.json`;
- runtime-specific continuation launcher.

## Production Claim Policy

Conformance v2 rejects unsupported production claims.

Allowed claim:
- source-backed workspace install/update and packaged runtime contract.

Blocked claim:
- live runtime session verified, unless there is explicit live evidence.

Every runtime fixture must include limitations so the docs do not overstate verification.

## Validation

Run:

```bash
/aikit-doctor --check validate-adapter-conformance-v2
```

Related checks:
- `/aikit-doctor --check validate-adapter-continuation`
- `/aikit-doctor --check validate-adapter-fixtures`
