# CLI Agent Operating Protocol

Этот документ описывает, как Claude Code, Codex, GLM и OpenCode агенты должны использовать AIKit внутри terminal runtime.

Главный принцип: пользователь общается с CLI-моделью обычным языком, а агент сам выбирает profile, workflow, skill, memory и внутренние Python tools.

---

## Mental Model

AIKit состоит из двух слоёв:

- `human interface` — Claude/Codex/GLM/OpenCode CLI, где пользователь пишет задачу;
- `tooling layer` — Python scripts, manifests, memory и retrieval store, которые агент вызывает сам.

Пользователь не должен помнить команды вроде `run-agent-task.py`, `build-context-pack.py`, `run-workflow-hook.py`.
Эти команды являются внутренним инструментарием агента.

Runtime bundles также публикуют machine-readable registry:

```text
.aikit/runtime-tools.json
```

Перед выбором внутренних команд агент должен использовать registry как source of truth, а этот документ — как поведенческий protocol.

Если задача запускается через `scripts/run-agent-task.py`, агент должен сначала посмотреть `recommended_tools` в orchestration packet.
Этот блок уже применяет registry к текущему intent, target path, hook context и validation needs.

---

## Default Agent Loop

Когда CLI-агент получает задачу:

1. Понять intent задачи и затронутый stack.
2. Найти подходящий profile или preset.
3. Собрать context pack через internal tooling, если задача требует routing, retrieval, workflow или RAG context.
4. Выполнить работу в коде или документации.
5. Обновить memory, если появились устойчивые решения, workflow-паттерны или важный проектный контекст.
6. Обновить knowledge store, если менялись источники retrieval context.
7. Прогнать validation matrix.
8. Вернуть человеку краткий отчёт: что сделано, какие проверки прошли, что осталось.

---

## Internal Tooling Policy

Агент может использовать внутренние скрипты, когда они помогают принять решение или сохранить состояние.
В installed runtime workspace сначала проверь `.aikit/runtime-tools.json`; таблица ниже является human-readable fallback:

| Сценарий | Tool |
| --- | --- |
| Нужно выбрать profile/workflow/skill | `/aikit-run-task --task "<task>" --json` |
| Нужно собрать retrieval/memory-aware context pack | `/aikit-knowledge-refresh --context-pack --task "<task>" --profile <profile> --json` |
| Нужно зафиксировать durable task memory в `.aikit/memory/` | `/aikit-command-center memory-capture --task "<task>" --profile <profile> --intent <intent>` |
| Нужно выполнить workflow hook | `/aikit-command-center workflow-hook ... --json` |
| Нужно обновить knowledge store | `/aikit-knowledge-refresh --rebuild` |
| Нужно проверить drift knowledge | `/aikit-knowledge-refresh --check-drift` |
| Нужно проверить конфиги | `/aikit-doctor --check validate-config` |

Knowledge tools являются отдельной family внутри runtime registry:
- `query` — найти knowledge до edits (`context-pack-builder`);
- `memory` — записать durable repository context в canonical memory (`memory-capture-writer`);
- `maintenance` — пересобрать retrieval runtime (`knowledge-store-builder`);
- `governance` — проверить freshness и coverage (`knowledge-drift-detector`).

Registry также поддерживает `mcp-tool` как runtime-native tool type:
- tool исполняется через MCP/provider layer runtime;
- у него нет обязательной shell-команды;
- он должен публиковать `provider`, `runtime_binding`, `availability`, `adapter_support`.

Registry fields:

- `name` — стабильное имя tool для агентного reasoning;
- `family` — logical tool family (`knowledge`, `runtime`, ...);
- `kind` — role inside family (`query`, `maintenance`, `governance`, `validation`, ...);
- `tool_type` — implementation form, сейчас поддерживаются `local-script` и `mcp-tool`;
- `provider` — MCP/native provider name для `mcp-tool`;
- `runtime_binding` — canonical runtime binding for MCP-backed tools;
- `availability` — how the tool is surfaced by the runtime (`runtime-native`, etc.);
- `adapter_support` — adapters expected to understand this MCP-backed tool surface;
- `command` — базовая команда, к которой агент добавляет аргументы;
- `policy` — safety policy для запуска;
- `safe_to_auto_run` — можно ли tool безопасно auto-run внутри runtime policy;
- `write_scope` — high-level write semantics (`read-only`, `knowledge-store-cache`, `runtime-journal`, ...);
- `inputs` — canonical inputs для tool;
- `usage_when` / `blocked_when` — explainable trigger boundaries;
- `requires_repo_root` — tool должен запускаться из workspace, где есть AIKit `scripts/` и source layers;
- `when_to_use` — ситуации, где tool уместен;
- `writes` — ожидаемые write scopes;
- `requires_approval` — нужен ли явный human approval.

Runtime packet fields:

- `tool_registry` — metadata о подключённом registry;
- `knowledge_tooling` — explicit knowledge-family projection: available tools, recommended knowledge tools, invocations and phase mapping.
- `mcp_tooling` — explicit runtime-native MCP/provider projection for non-shell tools.
- `external_knowledge_bridge` — hybrid bridge contract between canonical repo knowledge and live provider-backed knowledge/action surfaces.
- `tool_family_routing` — explainable routing layer between knowledge, memory, local runtime tools and runtime-native provider actions.
- `memory_lifecycle` — active/archive state of canonical memory plus archive hygiene recommendation when task-memory pressure grows.
- `routing_guidance` — routing review layer with sanity checks, override candidates and ready rerun commands when profile matching is ambiguous.
- `recommended_tools` — task-specific shortlist tools, которые агенту стоит использовать в этой задаче.
- `recommended_tool_invocations` — task-specific invocation hints со статусом `ready`, `needs-input` или `runtime-native`.
- `tool_execution_plan` — phased handoff по внутренним tools: `orient`, `execute`, `validate`, `finalize`.
- `agent_work_order` — единый handoff packet для следующего CLI-агента.
- `phase_executions` — результат safe auto-run для выбранных фаз.
- `runtime_execution_report` — агрегированный runtime status: что completed, что blocked, что pending и какие follow-up нужны дальше.
- `runtime_observation_log` — normalized execution observations and enrichment hints after runtime hops.
- `agent_handoff_prompt` — готовый текстовый handoff, который можно напрямую передать следующему CLI-агенту.
- `agent_handoff_bundle` — файловый bundle со stable artifact paths для handoff между сессиями и runtime.
- `resumed_from` — путь к bundle/journal, если текущий orchestration run был восстановлен из сохранённого handoff.
- `continuation_state` — resumable state layer с completed steps и status из предыдущего runtime run.
- `suggested_next_runtime_action` — machine-readable safest next step для текущего runtime state.
- `allow_rerun_completed` — explicit override, если resumed auto-run должен повторно исполнить уже закрытые steps.
- `session_lineage` — chain metadata для parent/root/depth между continuation runs.

Правило исполнения:

- если invocation имеет статус `ready`, агент может использовать его как canonical starting command;
- если invocation имеет статус `needs-input`, агент должен сначала заполнить missing inputs или выбрать другой tool;
- если есть и `recommended_tools`, и `recommended_tool_invocations`, приоритет у invocation layer.
- если есть `knowledge_tooling`, агенту стоит сначала проверить, не нужен ли explicit knowledge step до edits или перед finalize.
- если есть `mcp_tooling`, агенту нужно различать runtime-native tools и shell tools; `mcp-tool` не должен исполняться как локальная команда.
- если есть `external_knowledge_bridge`, агенту стоит использовать его как hybrid context contract: сначала repo-authored knowledge, затем provider-backed knowledge, затем external action.
- если есть `tool_family_routing`, агенту стоит использовать его как policy explanation: почему task идёт через retrieval, memory, validation или provider hop именно в таком порядке.
- если есть `routing_guidance`, агенту стоит сначала проверить `review_level`; при `high` routing не должен восприниматься как безусловно надёжный.
- если есть `routing_guidance.resolution_options`, агенту стоит использовать их как canonical rerun commands для keep-current или manual override, а не собирать `run-agent-task.py --profile ... --intent ...` вручную.
- если есть `tool_execution_plan`, именно он задаёт порядок применения tools в задаче.
- если есть `agent_work_order`, он является главным source of truth для старта и завершения задачи.
- если используется `--auto-run-phase`, агент должен доверять только `phase_executions` для факта выполненных safe steps.
- если есть `runtime_execution_report`, его следует использовать как основной status layer для handoff между CLI-агентами.
- если есть `runtime_observation_log`, агенту стоит использовать его как enrichment layer: какие events реально произошли и что теперь имеет смысл усилить в memory или knowledge.
- если есть `memory_lifecycle` и там `archive_recommended = true`, агенту стоит учитывать `memory-task-archiver` как maintenance follow-up, но не запускать его без осмысленного cutoff.
- если нужен быстрый переход между runtime или сессиями, `agent_handoff_prompt` можно использовать как canonical user-facing continuation prompt.
- если continuation должен пережить завершение текущей сессии, агенту стоит опираться на `agent_handoff_bundle` и его artifact paths.
- если нужно продолжить предыдущую CLI-сессию без ручного пересказа контекста, агент может запускать `run-agent-task.py --resume-from-bundle <bundle>` как canonical resume path.
- если packet содержит `continuation_state`, агенту нужно учитывать previous-run completion и не трактовать такие steps как новый pending work.
- если packet содержит `suggested_next_runtime_action`, агенту стоит использовать его как preferred next step, если нет более сильного human override.
- если `suggested_next_runtime_action.kind = use-runtime-provider`, следующий шаг должен выполняться через MCP/provider layer текущего runtime.
- при resumed auto-run агент должен по умолчанию ожидать `skipped` для already completed steps и использовать `--allow-rerun-completed` только как явный override.
- если packet содержит `session_lineage`, агент может использовать его для понимания глубины continuation и связи текущего run с предыдущими.

Safe execution режим:

```bash
/aikit-run-task --task "<task>" --execute-policy safe --json
```

Используй `--execute-policy safe` только для allowlisted automation hops.
Если команда содержит placeholder path, сначала замени его реальным файлом или оставь человеку явный follow-up.

---

## Memory Rules

Canonical memory path:

```text
.aikit/memory/
```

Пиши в memory только то, что будет полезно в будущих задачах:

- устойчивые архитектурные решения;
- повторяющиеся workflow-паттерны;
- known pitfalls;
- правила развития AIKit;
- выводы после нескольких похожих задач.

Не пиши в memory:

- одноразовый шум;
- полные логи команд;
- временные детали, которые не помогают будущему агенту.

После изменения canonical memory синхронизируй mirror/runtime state, если текущий adapter этого требует.

---

## RAG And Knowledge Store Rules

Knowledge store является runtime cache, а не source of truth.

Source of truth:

- `base/`
- `profiles/`
- `packs/`
- `docs/`
- `.aikit/memory/`
- `knowledge/`

Если агент меняет документы, manifests, agents, skills или memory, и это влияет на retrieval context, он должен использовать knowledge tools осознанно:

- `query`: получить retrieval/memory-aware context;
- `maintenance`: обновить runtime knowledge store;
- `governance`: проверить drift и freshness.

Если knowledge sources реально изменились, он должен обновить store:

```bash
/aikit-knowledge-refresh --rebuild
```

Если есть риск stale context, проверь drift:

```bash
/aikit-knowledge-refresh --check-drift
```

---

## Validation Matrix

Перед завершением изменений агент должен выполнить минимальную проверку:

```bash
/aikit-doctor --check validate-config
PYTHONPYCACHEPREFIX=/tmp/codex-pycache python3 -m py_compile scripts/*.py
git diff --check
```

Если менялись adapter bundles или runtime entrypoints, добавь smoke build:

```bash
/aikit-install-update build codex --profile vue-nuxt --target /tmp/aikit-builds
/aikit-install-update build glm --profile vue-nuxt --target /tmp/aikit-builds
/aikit-install-update build opencode --profile vue-nuxt --target /tmp/aikit-builds
```

---

## Report Format

В конце работы агент возвращает короткий отчёт:

```text
AIKIT_RUNTIME_REPORT

Task:
- <что делали>

Runtime decisions:
- Profile: <profile>
- Workflow: <workflow or n/a>
- Internal tools used: <scripts or none>

Changes:
- <главные изменения>

Validation:
- <команды и результат>

Next:
- <следующий полезный шаг>
```
