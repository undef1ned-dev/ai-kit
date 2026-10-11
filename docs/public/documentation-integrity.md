# Documentation Integrity

`P12-E9` adds a local documentation integrity check and a generated HTML roadmap.

## Checks

[scripts/validate-documentation-integrity.py](../../scripts/validate-documentation-integrity.py) verifies:

- local Markdown links in `docs/**/*.md` resolve inside the repository;
- repo-absolute Markdown links are rejected inside `docs/public/**/*.md`;
- completed Phase 12 epics reference existing primary artifacts;
- Phase 12 epic statuses match between [docs/phase-execution/P12.md](../phase-execution/P12.md) and [docs/phase-execution/P12-execution-plan.json](../phase-execution/P12-execution-plan.json);
- [docs/roadmap.html](../roadmap.html) was generated from the current [docs/roadmap.md](../internal/roadmap.md) content.

[scripts/validate-repo-relative-links.py](../../scripts/validate-repo-relative-links.py) verifies:

- enforced tracked surfaces such as `README.md`, `docs/public/**` and `scripts/**/*.py` stay free from workstation-specific absolute paths;
- after `P131`, the former `.aikit/**` and `.claude/**` deferred scopes are closed and tracked workstation-specific absolute paths must stay at zero across the repository by [docs/fixtures/repo-relative-link-fixtures.json](../fixtures/repo-relative-link-fixtures.json).

[scripts/validate-docs-taxonomy.py](../../scripts/validate-docs-taxonomy.py) verifies:

- every file in `docs/` is classified by [docs/docs-surface-manifest.json](../docs-surface-manifest.json);
- classification is one-to-one (no uncategorized and no multi-category overlap);
- every required category is present and owned.

## Roadmap HTML

Generate the HTML roadmap with:

```bash
/aikit-docs --refresh roadmap-html
```

The generated file embeds a SHA-256 hash of `docs/roadmap.md`. The validator fails if the HTML hash is stale.

This is a local artifact for private repository use. GitHub Pages remains out of scope because this repository is private and Pages is unavailable on the current plan.

## Validation

```bash
/aikit-docs --refresh roadmap-html
/aikit-doctor --check validate-documentation-integrity
/aikit-doctor --check validate-repo-relative-links
/aikit-doctor --check validate-docs-taxonomy
```
