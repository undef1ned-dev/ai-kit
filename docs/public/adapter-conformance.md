# Adapter Conformance

Этот документ фиксирует conformance contract для runtime adapters AIKit.

Его задача:
- определить, что именно должен уметь adapter на каждом уровне зрелости;
- связать это с проверяемыми fixture/scenario правилами;
- убрать размытость между `planned`, `experimental` и `active`.

Связанные артефакты:
- [docs/manifest-spec.md](./manifest-spec.md)
- [docs/fixtures/adapter-fixtures.json](../fixtures/adapter-fixtures.json)
- [scripts/validate-adapter-fixtures.py](../../scripts/validate-adapter-fixtures.py)
- [docs/adapter-conformance-v2.md](./adapter-conformance-v2.md)
- [scripts/validate-adapter-conformance-v2.py](../../scripts/validate-adapter-conformance-v2.py)

---

## Conformance Levels

### `planned`

Adapter может считаться `planned`, если:
- есть валидный `adapter.manifest.json`;
- есть packaging contract;
- если заявлен `continuation_prompt`, для него есть template;
- adapter не заявляет install/update contract без реальной реализации.

### `experimental`

Adapter может считаться `experimental`, если:
- проходит manifest validation;
- собирается через `build-adapter-package.py`;
- если заявлен `install_script`, install flow проходит smoke-check;
- bundle или workspace содержит ожидаемые launcher files;
- continuation path существует для adapter’ов, которые целятся в practical use.

### `active`

Adapter может считаться `active`, если:
- у него есть production-ready install/update contract;
- runtime layout соответствует declared generated artifacts;
- validation и install/update сценарии воспроизводимы как часть repo workflow;
- adapter используется как основной или production-supported runtime.

Для workspace-sync adapters это означает, что:
- install flow воспроизводимо создаёт runtime workspace;
- update flow воспроизводимо пересинхронизирует уже установленный workspace;
- continuation и runtime entrypoints остаются валидными после update.

---

## Required Capabilities By Field

### Manifest-only requirements
- `runtime`
- `status`
- `config_roots`
- `generated_artifacts`
- `memory_path`
- `source_layers`

### Build-level requirements
- успешный `build-adapter-package.py`
- совместимость pack compatibility checks
- генерация `AIKIT.md`
- генерация `.aikit/adapter.manifest.json`

### Install-level requirements
- успешный `/aikit-runtime-workspace` lifecycle command или runtime-native install flow
- наличие `.aikit/INSTALL.md`
- наличие runtime launcher files внутри config roots
- seeded memory в declared `memory_path`
- наличие `.aikit/runtime-entrypoints.json` как runtime execution contract

### Continuation-level requirements
- continuation prompt существует, если adapter позиционируется как practical runtime
- continuation prompt ведёт к packaged maintainer surface
- prompt использует declared `memory_path`

### Runtime execution requirements
- adapter manifest объявляет `runtime_entrypoints`
- каждый execution entrypoint привязан к real generated artifact
- runtime workspace содержит `entrypoints.json` внутри runtime config root, если adapter имеет directory-based config root
- entrypoint layer объясняет, где читать guide, где продолжать maintainer handoff и где лежит packaged agent surface

---

## Current Matrix

| Adapter | Status | Build | Install | Continuation | Notes |
|---------|--------|-------|---------|--------------|-------|
| `claude` | `active` | yes | yes | n/a | production adapter через `attach.sh` / `update.sh` |
| `codex` | `active` | yes | yes | yes | workspace-sync install + update flow, production-supported runtime |
| `glm` | `active` | yes | yes | yes | workspace-sync install + update flow, production-supported runtime |
| `opencode` | `active` | yes | yes | yes | workspace-sync install + update flow, production-supported runtime |

---

## Policy

Нельзя повышать adapter в зрелости только по prose или желанию.

Conformance v2 also requires limitations for every runtime so source-backed install/update and continuation validation is not overstated as live runtime verification.

Повышение статуса должно сопровождаться:
1. изменением manifest;
2. обновлением fixture expectations;
3. прохождением validator / smoke-check;
4. обновлением docs и execution log.

---

## Why This Matters

Conformance matrix делает runtime support проверяемым.

Без неё:
- `experimental` и `active` легко становятся маркетинговыми словами;
- разные adapters развиваются по разным скрытым правилам;
- maintainer-agent не может надёжно отвечать, что реально поддерживается.
