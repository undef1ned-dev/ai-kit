# AIKit Docs Site

This directory is the public documentation site surface for AIKit.

It is intentionally separate from:

- `docs/public`, which remains source material;
- private maintainer documentation;
- generated local dashboards;
- repository planning and validation fixtures.

## Local Preview

Preview with a Mintlify-compatible CLI:

```bash
cd docs-site
npx mint dev
```

Production hosting is not configured here. Choose the hosting provider, domain and credential flow before publishing.

## Validation

Run from the repository root:

```bash
python3 scripts/validate-docs-site-boundary.py
python3 scripts/validate-docs-site-nav.py
python3 scripts/validate-docs-site-content.py
python3 scripts/validate-public-surface-freshness.py
```
