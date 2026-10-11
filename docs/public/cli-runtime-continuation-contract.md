# CLI Runtime Continuation Contract

Этот документ фиксирует continuation contract для runtime adapters AIKit.

Его задача:
- дать единый adapter-level source of truth для resumed flows;
- объяснить, как использовать handoff bundle, continuation state и session lineage внутри installed workspace;
- синхронизировать Claude, Codex, GLM и OpenCode вокруг одного continuation поведения.

---

## Core Principle

Пользователь продолжает работать через CLI модели.

AIKit runtime под капотом должен:
- подхватывать сохранённый bundle;
- восстанавливать state прошлой сессии;
- показывать safest next runtime action;
- не повторять уже завершённые steps без явного override;
- сохранять lineage между continuation runs.

---

## Canonical Continuation Artifacts

В installed workspace continuation опирается на:
- `.aikit/runtime-operating-protocol.md`
- `.aikit/runtime-tools.json`
- `.aikit/runtime-entrypoints.json`
- runtime journal `<timestamp>-<task>.json`
- handoff prompt `<timestamp>-<task>.handoff.md`
- bundle manifest `<timestamp>-<task>.bundle.json`

Если continuation запускается из bundle, именно `.bundle.json` считается canonical entry artifact.

File-level journal and bundle shape is documented in [docs/runtime-journal-contract.md](../internal/runtime-journal-contract.md).

---

## Resume Contract

Canonical resume path:

```bash
/aikit-run-task --resume-from-bundle <bundle-or-journal> --json
```

Runtime должен восстановить:
- `task`
- `profile`
- `intent`
- `target_path`
- `target_kind`
- `continuation_state`
- `session_lineage`

CLI-агент не должен требовать от пользователя ручного пересказа этого контекста, если bundle уже существует.

---

## Continuation State Contract

`continuation_state` нужен, чтобы resumed flow:
- видел completed steps из предыдущего run;
- отличал previous-run completion от current-run completion;
- не трактовал carried completion как новый pending work.

Минимальные expectations:
- `previous_completed_steps`
- `current_completed_steps`
- `previous_missing_inputs`
- `previous_status`
- `resumed`
- `completion_scope`

`completion_scope` фиксирует имена полей, через которые runtime и validators различают carried completion and current completion:
- `previous_run_field`: `previous_completed_steps`
- `current_run_field`: `current_completed_steps`
- `report_previous_run_field`: `previous_run_completed_steps`
- `report_current_run_field`: `current_run_completed_steps`

Это разделение обязательно: шаг, завершённый в previous run, может скрывать pending work, но не должен выглядеть как newly completed current-run work.

Packet-construction orient steps (`agent-task-router`, `context-pack-builder`) are recomputed on every run and are not carried as previous-run completion.

---

## Suggested Next Step Contract

`suggested_next_runtime_action` — preferred next step для CLI-агента.

Порядок приоритета:
1. unblock missing inputs
2. resolve blocked step
3. run pending ready tool
4. close task
5. continue from entrypoint as fallback

Если adapter bundle содержит этот field, continuation launcher и runtime guide должны считать его preferred next-step hint.

Handoff prompt должен повторять тот же next action в секции `Suggested next runtime action`, чтобы человек и runtime видели одинаковый следующий шаг.

---

## Resume-Aware Auto-Run Contract

При resumed auto-run:
- already completed steps должны по умолчанию получать статус `skipped`;
- skipped steps должны попадать в `runtime_execution_report.skipped_steps`, а не в `blocked_steps`;
- повторный запуск допустим только через explicit override:

```bash
/aikit-run-task --resume-from-bundle <bundle> --auto-run-phase finalize --allow-rerun-completed --json
```

То есть default behavior:
- `skip repeated safe steps`
- `preserve blockers`
- `avoid silent reruns`

---

## Session Lineage Contract

Каждый continuation run должен сохранять:
- `run_id`
- `parent_run_id`
- `root_run_id`
- `depth`

Назначение:
- видеть history chain между runtime runs;
- понимать, какой run является root source для текущего continuation;
- готовить базу для future `next_session_packet`.

Lineage должен сохраняться и в runtime journal, и в handoff bundle manifest, чтобы следующий resume мог восстановить chain из любого canonical entry artifact.

---

## Adapter Expectations

Для `Codex`, `GLM` и `OpenCode` bundle должен:
- публиковать continuation prompt;
- публиковать runtime operating protocol;
- публиковать runtime tools registry;
- публиковать continuation contract;
- держать эти entrypoints в adapter manifest и runtime entrypoints registry.

Это нужно, чтобы любой из этих runtime:
- одинаково понимал resumed flow;
- одинаково читал bundle artifacts;
- одинаково продолжал maintainer workflow без runtime-specific развилок.

Для `Claude` readiness surface другой:
- Claude остаётся active baseline adapter through `scripts/attach.sh` and `scripts/update.sh`;
- continuation readiness проверяется через direct core docs, `CLAUDE.md`, `.claude/*`, memory mirror and runtime graph;
- Claude fixture не заявляет packaged bundle parity with `build-adapter-package.py`.

Adapter readiness является fixture-backed contract, not live production verification. Проверка readiness не означает, что внешний CLI/TUI session был запущен.

---

## What Adapters Should Tell The Agent

Continuation launcher внутри adapter bundle должен подсказывать:
- прочитать `.aikit/runtime-operating-protocol.md`;
- прочитать `.aikit/runtime-continuation-contract.md`;
- использовать `.aikit/runtime-tools.json` как tool registry;
- использовать bundle/journal как source of truth для resumed tasks;
- не повторять already completed steps без явной причины.

## Readiness Validation

Adapter-native readiness валидируется отдельно:

```bash
/aikit-doctor --check validate-adapter-continuation
```

Validator читает `docs/fixtures/adapter-continuation-fixtures.json`, сверяет manifests/templates, build-probes packaged adapters locally, and requires every fixture to keep `live_production_verification: false`.

## Runtime Packet Regression Fixtures

High-level packet shape валидируется отдельно от field-level continuation fixtures:

```bash
/aikit-doctor --check validate-runtime-packet-fixtures
```

Этот validator читает `docs/fixtures/runtime-packet-fixtures.json` and covers:
- resume from generated handoff bundle;
- missing-input continuation;
- validation-only auto-run continuation;
- finalize continuation after previous validation completion.

Эти fixtures проверяют top-level packet fields, `continuation_state`, `runtime_execution_report`, `session_lineage`, `suggested_next_runtime_action` and human handoff alignment together.
