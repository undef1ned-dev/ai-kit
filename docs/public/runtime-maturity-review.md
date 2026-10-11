# Runtime Maturity Review

Этот документ фиксирует текущий maturity review для non-Claude adapters AIKit.

Его цель:
- честно показать, какие runtime уже можно считать production-supported внутри AIKit;
- отделить `active` support от просто “есть manifest и install script”;
- зафиксировать, почему `Codex`, `GLM` и `OpenCode` получили текущий maturity verdict.

Связанные артефакты:
- [docs/adapter-conformance.md](./adapter-conformance.md)
- [docs/fixtures/adapter-fixtures.json](../fixtures/adapter-fixtures.json)
- [docs/adapter-runtime-execution.md](./adapter-runtime-execution.md)
- [docs/adapter-graph-execution.md](../internal/adapter-graph-execution.md)

---

## Verdict

| Adapter | Previous status | Current status | Verdict |
|---------|-----------------|----------------|---------|
| `codex` | `experimental` | `active` | promoted |
| `glm` | `experimental` | `active` | promoted |
| `opencode` | `experimental` | `active` | promoted |

---

## Why Codex Is Now Active

`Codex` satisfies the current active contract because:
- build flow работает стабильно через `scripts/build-adapter-package.py`;
- пользовательский runtime lifecycle flow воспроизводим через `/aikit-runtime-workspace`;
- install/update scripts остаются internal implementation layer за slash command;
- runtime workspace публикует:
  - `.codex/AIKIT.md`
  - `.codex/CONTINUE_AIKIT_MAINTAINER.md`
  - `.codex/entrypoints.json`
  - `.codex/runtime-graph.json`
  - `.aikit/runtime-entrypoints.json`
  - `.aikit/runtime-graph.json`
- continuation path уже используется как practical bridge для развития AIKit в Codex runtime.

## Why GLM Is Now Active

`GLM` получает тот же maturity jump, потому что:
- использует тот же validated install/update contract;
- получает runtime-native guide, continuation prompt и entrypoint/graph artifacts;
- поддерживает seeded canonical memory в `.aikit/memory/`;
- для AIKit это уже production-supported runtime surface, а не только planned target.

## Why OpenCode Is Now Active

`OpenCode` получает maturity jump, потому что:
- install/runtime surface уже есть и валидируется;
- continuation prompt и structured execution artifacts уже опубликованы;
- update flow оформлен как `/aikit-runtime-workspace ... --operation update` поверх internal scripts;
- adapter проходит ту же install/update parity-модель, что и `Codex` с `GLM`;
- для AIKit это теперь production-supported runtime, а не только exploratory target.

---

## Promotion Criteria Used In This Review

Adapter поднимается в `active`, если одновременно выполняются условия:
- есть отдельный и воспроизводимый install/update contract;
- runtime entrypoints и graph artifacts переживают install/update smoke-pass;
- continuation path ведёт к packaged maintainer surface без runtime-specific ручных допущений;
- adapter включён в product-facing docs как production-supported runtime.

---

## Next Review Questions

- Нужно ли выделить отдельный status между `experimental` и `active`, если появятся runtime с partial production support?
- Хотим ли мы добавить runtime-specific update fixtures с проверкой `UPDATE.md` и resync semantics?
