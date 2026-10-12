# Local Docs Portal Navigation

The local docs portal is the private-repository compatible navigation layer for AIKit. It is built from local static files, uses relative links and does not require GitHub Pages.

Fixtures:
- [docs/fixtures/local-docs-portal-fixtures.json](../fixtures/local-docs-portal-fixtures.json)

Validator:
- [scripts/validate-local-docs-portal.py](../../scripts/validate-local-docs-portal.py)

## Private Repo Rules

- does not require GitHub Pages
- local static files
- relative links

## Start

- [Product Story](../public/product-story.md)
- [Get Started](../public/get-started.md)
- [HTML Catalog](../catalog.html)

## Audience Paths

- External project adoption:
  [Get Started](../public/get-started.md),
  [Install Matrix](../public/install-matrix.md),
  [Runtime Maturity Review](../public/runtime-maturity-review.md),
  [Marketplace](../public/marketplace.md)
- Internal repository development:
  [Docs Surface Map](../../README.md),
  [Roadmap HTML](../roadmap.html),
  [Phase 15](../phase-execution/P15.md),
  [Execution Log](../internal/execution-log.md)

## Catalog And Workflow

- [Catalog UX V2](./catalog-ux-v2.md)
- [Workflow Templates](../internal/workflow-presets-task-templates.md#./workflow-presets-task-templates.md)
- [Choose Best Agent](../internal/choose-best-agent-flow.md#./choose-best-agent-flow.md)

## Governance

- [Product Governance](./agent-workflow-product-governance.md)
- [Backend Frontend Agent Skills Plan](./backend-frontend-agent-skills-plan.md)
- [Roadmap HTML](../roadmap.html)
- [Phase 15](../phase-execution/P15.md)
- [Execution Log](../internal/execution-log.md)

## Runtime Guides

- [OpenCode Runtime Guide](../public/opencode-runtime-guide.md)
- [Runtime Maturity Review](../public/runtime-maturity-review.md)
- [Install Matrix](../public/install-matrix.md)

## Regeneration

```bash
/aikit-docs --refresh profile-docs
/aikit-docs --refresh roadmap-html
```

## Validation

```bash
/aikit-doctor --check validate-local-docs-portal
/aikit-doctor --check validate-documentation-integrity
```
