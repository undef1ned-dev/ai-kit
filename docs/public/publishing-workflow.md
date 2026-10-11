# Publishing Workflow

Этот документ генерируется из marketplace manifest и описывает distribution surface для packs, presets и adapters.

## Distribution Channels

| Channel | Kind | Targets | Delivery |
|---------|------|---------|----------|
| `docs-surface` | `documentation` | `packs`, `presets`, `adapters` | Generated markdown and HTML docs inside docs/. |
| `workspace-install` | `runtime-install` | `presets`, `adapters` | attach/build/install/update scripts for Claude and runtime adapters. |
| `artifact-bundles` | `distribution-artifact` | `presets`, `adapters` | Built adapter bundles and generated docs artifacts for internal sharing. |

## Publishing Workflows

### `pack-curation`

- Target kind: `pack`
- Owner: `aikit-maintainer`
- Delivery channels: `docs-surface`
- Eligibility:
  - pack.json is valid
  - compatible_profiles references real profiles
  - skills and agents exist
  - validate-config passes

### `preset-distribution`

- Target kind: `preset`
- Owner: `aikit-maintainer`
- Delivery channels: `docs-surface`, `workspace-install`, `artifact-bundles`
- Eligibility:
  - preset manifest is valid
  - recommended_adapter references a supported runtime
  - preset resolves through resolve-preset.py
  - validate-config passes

### `adapter-promotion`

- Target kind: `adapter`
- Owner: `aikit-maintainer`
- Delivery channels: `docs-surface`, `workspace-install`, `artifact-bundles`
- Eligibility:
  - adapter manifest is valid
  - build/install fixtures pass
  - if active: update contract exists
  - maturity review is documented

## Reading This Surface

- Start with `docs/public/marketplace.md` to compare packs, presets and adapters.
- Use `docs/public/install-matrix.md` when you need install/update commands for a chosen runtime.
- Use `docs/public/release-center.md` when you need release-state context before adoption.
