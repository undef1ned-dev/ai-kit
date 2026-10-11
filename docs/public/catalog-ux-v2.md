# Catalog UX V2

Catalog UX V2 is the local, private-repository compatible entry point for discovering AIKit profiles, runtimes, workflows, evidence surfaces and validators.
The generated HTML surface now presents this as a public-facing `Catalog Overview` instead of an internal UX-program label.

Human entry starts at [docs/public/start-here.md](./start-here.md). The generated agents and skills registry lives at [docs/public/agents-skills-reference.md](./agents-skills-reference.md) and should be treated as reference, not the first task-selection surface.

Source artifact:
- [docs/catalog.html](../catalog.html)
- [Phase 31 requirements](../phase-execution/P31.md)

Generator:
- [scripts/generate-catalog.py](../../scripts/generate-catalog.py)

## Product Contract

The catalog must answer five questions before a user starts a workflow:

1. Which profile or pack should own the task?
2. Which runtime adapter can run the workflow?
3. Which workflow recipe or entry path is expected?
4. Which evidence surfaces can support implementation or review?
5. Which validation commands prove the local docs and routing contracts still work?

## Catalog Surfaces

| Surface | Source | Purpose |
| --- | --- | --- |
| Profiles and packs | `base/`, `profiles/`, `packs/` | Browse agents, skills, default chains and capability modes. |
| Runtime choices | `adapters/*/adapter.manifest.json` | Compare Claude, Codex, GLM and OpenCode adapter status and install type. |
| Workflow surfaces | `profiles/*/workflow.manifest.json` | Show default recipes, recipe counts and frontend task workflow availability. |
| Evidence surfaces | `knowledge/project-evidence.manifest.json`, `knowledge/multi-source-registry.manifest.json`, `knowledge/storage/manifest.json` | Show which project, knowledge and storage sources can feed context. |
| Validation commands | product, workflow, documentation and config validators | Keep generated catalog output tied to repo contracts. |

## Generation

Regenerate the catalog after changing agents, skills, profile manifests, runtime adapters, workflow manifests or evidence registries:

```bash
/aikit-docs --refresh catalog
```

The generator writes only a static HTML file. It does not require public hosting, GitHub Pages, external assets or a running service.

## Validation

Run the product and documentation validators after regeneration:

```bash
/aikit-doctor --check validate-product-docs
/aikit-doctor --check validate-documentation-integrity
/aikit-doctor --check validate-config
```

For workflow-oriented catalog changes, also run:

```bash
/aikit-doctor --check validate-workflow-fixtures
/aikit-doctor --check validate-tool-family-routing-fixtures
```

## UX Rules

- Keep the first viewport practical: totals, runtime choices, workflow surfaces, evidence surfaces and validation commands should be visible before deep profile browsing.
- Keep links local and relative where possible.
- Do not introduce a public hosting dependency.
- Do not claim live runtime verification from static catalog data.
