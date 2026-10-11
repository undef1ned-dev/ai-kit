# Manifest Spec

Этот документ фиксирует канонический spec layer для структурированных артефактов AIKit.

Его задача:
- явно описать поддерживаемые типы manifests;
- снизить зависимость системы от prose-only договорённостей;
- дать stable contract для validators, generators и будущих adapters.

Связанные schema-файлы:
- [schemas/agent.frontmatter.schema.json](../../schemas/agent.frontmatter.schema.json)
- [schemas/skill.frontmatter.schema.json](../../schemas/skill.frontmatter.schema.json)
- [schemas/profile.manifest.schema.json](../../schemas/profile.manifest.schema.json)
- [schemas/capabilities.schema.json](../../schemas/capabilities.schema.json)
- [schemas/adapter.manifest.schema.json](../../schemas/adapter.manifest.schema.json)
- [schemas/pack.schema.json](../../schemas/pack.schema.json)
- [schemas/workflow-policy.schema.json](../../schemas/workflow-policy.schema.json)
- [schemas/workflow.manifest.schema.json](../../schemas/workflow.manifest.schema.json)
- [schemas/preset.schema.json](../../schemas/preset.schema.json)
- [schemas/marketplace.schema.json](../../schemas/marketplace.schema.json)
- [schemas/knowledge.model.schema.json](../../schemas/knowledge.model.schema.json)
- [schemas/knowledge.source.schema.json](../../schemas/knowledge.source.schema.json)
- [schemas/knowledge.store.schema.json](../../schemas/knowledge.store.schema.json)
- [schemas/knowledge.retrieval.schema.json](../../schemas/knowledge.retrieval.schema.json)
- [schemas/knowledge.governance.schema.json](../../schemas/knowledge.governance.schema.json)
- [schemas/uikit.manifest.schema.json](../../schemas/uikit.manifest.schema.json)
- [schemas/api-surface.manifest.schema.json](../../schemas/api-surface.manifest.schema.json)
- [schemas/runtime-tools.manifest.schema.json](../../schemas/runtime-tools.manifest.schema.json)

## Supported Manifest Types

### Agent Frontmatter
- Paths: `base/agents/*.md`, `profiles/*/agents/*.md`, `packs/*/agents/*.md`
- Required: `name`, `description`, `tools`, `model`, `version`, `profile`, `tags`
- Optional: `example_prompt`, `output_block`, `depends_on`, `context_files`, `context_blocks`, `requires_mcp`

### Skill Frontmatter
- Paths: `base/skills/*.md`, `profiles/*/skills/*.md`, `packs/*/skills/*.md`
- Required: `name`, `profile`
- Usually required for non-template skills: `description`, `version`
- Optional: `tags`, `orchestrates`, `example_prompt`, `template`, `tvar_*`

### Profile Manifest
- Paths: `profiles/*/profile.manifest.json`
- Required: `profile`, `label`, `domain`, `taxonomy`, `keywords`, `path_signals`, `default_chain`, `recommended_skills`, `review_agent`, `tester_agent`, `capability_manifest`, `workflow_manifest`, `recommended_packs`
- `domain` remains the legacy routing domain used by existing runtime and knowledge consumers.
- `taxonomy` is the canonical normalization layer and must include:
  - `operating_class`
  - `direction`
  - `ecosystem`
  - `framework`
  - `domain_family`
  - `stack_profile`
  - `core_role_set`
  - `specialized_role_set`
  - `global_role_set`
  - `role_aliases`
  - `pack_compatibility`
  - `special_surfaces`
  - `workflow_contract`
- `operating_class` distinguishes normal product-project profiles from `meta-platform` operating surfaces.
- `direction -> ecosystem -> framework` is the canonical expansion model for profile families such as frontend/Vue-Nuxt, frontend/React, backend/Python, backend/PHP and backend/Rust.
- `domain_family + stack_profile` remains the compatibility target model; legacy `domain` stays as a compatibility layer until a later governed migration.
- `role_aliases` maps canonical role vocabulary to current legacy agent ids, so naming compatibility can improve without mass rename.
- `pack_compatibility.recommended` must stay aligned with root `recommended_packs`.

### Profile Directions Manifest
- Paths: `knowledge/profile-directions.manifest.json`
- Required: `version`, `status`, `model`, `directions`
- Role: canonical registry for global profile directions. It groups flat profile folders into `direction -> ecosystem -> framework` without forcing an immediate physical directory migration.

### Capability Manifest
- Paths: `profiles/*/capabilities.json`
- Required top-level: `profile`, `description`, `modes`
- Required per mode: `name`, `file_globs`, `owned_by`, `suggested_skills`, `focus`

### Adapter Manifest
- Paths: `adapters/*/adapter.manifest.json`
- Required: `name`, `runtime`, `status`, `label`, `description`, `entrypoint_style`, `config_roots`, `generated_artifacts`, `memory_path`, `source_layers`
- Optional: `runtime_entrypoints`, `graph_execution`, `continuation_prompt`, `attach_script`, `update_script`, `install_script`, `install_type`, `notes`
- Required per runtime entrypoint: `name`, `path`, `kind`, `purpose`
- Required per graph execution block: `status`, `shared_artifact`, `supports_parallel_handoff`, `purpose`

### Pack Manifest
- Paths: `packs/*/pack.json`
- Required: `name`, `label`, `version`, `description`, `compatible_profiles`, `agents`, `skills`, `source`

### Preset Manifest
- Paths: `presets/*.json`
- Required: `name`, `label`, `description`, `profiles`, `packs`, `recommended_adapter`, `source`
- Role: reusable distribution bundle for team-level install flows and preset-based onboarding

### Marketplace Manifest
- Paths: `marketplace/marketplace.manifest.json`
- Required: `version`, `status`, `model`, `sections`, `featured`
- Required per section: `name`, `kind`, `source`, `description`
- Role: curated registry layer for packs, presets and runtime adapters as internal marketplace surface

### Workflow Policy Manifest
- Paths: `policies/workflow-policy.json`
- Required: `version`, `intent_rules`, `next_action_rules`, `default_actions`
- Role: structured contract for task intent detection and next-step recommendations after profile/capability matching
- Current intent families: `design-implementation`, `design-alignment`, `migration-work`, `debug-fix`, `repository-maintenance`, `refactor-only`, `new-artifact`, `small-patch`, `feature-work`, `test-only`, `review-only`

### Workflow Manifest
- Paths: `profiles/*/workflow.manifest.json`
- Required: `profile`, `default_recipe`, `recipes`
- Optional top-level normalization block: `workflow_taxonomy`
- `workflow_taxonomy` is used when domain workflow contracts and stack specialization need to be described separately from recipe steps.
- Recommended `workflow_taxonomy` fields:
  - `domain_family`
  - `domain_contract`
  - `stack_specialization`
  - `core_step_roles`
  - `specialized_step_roles`
- Required per recipe: `name`, `description`, `intents`, `execution_mode`, `steps`
- Required per step: `id`, `agent`, `role`
- Optional per step: `depends_on`, `input_blocks`, `output_block`
- Optional per step retrieval hook: `retrieval.mode`, `retrieval.script`, `retrieval.fallback`, `retrieval.output_block`, `retrieval.path_required`
- Optional per recipe delivery loop: `delivery_loop.mode`, `delivery_loop.script`, `delivery_loop.trigger_after`, `delivery_loop.required_blocks`, `delivery_loop.timeline_dir`, `delivery_loop.execution_runtime`, `delivery_loop.playbook_path`, `delivery_loop.fallback`
- Для runtime-автоматизации `delivery_loop.script` должен указывать на `scripts/run-delivery-loop.py`, который инкапсулирует comparison, execution-pack, playbook update, mirror sync и knowledge rebuild
- Для orchestration-уровня history-driven запусков используй `scripts/run-workflow-hook.py`: он читает recipe metadata, экспортирует `required_blocks` из workflow transcript и только затем вызывает `delivery_loop.script`
- Role: structured execution recipes for feature-delivery, review-pass, test-pass, design-to-code and future graph-based workflow orchestration

### Release Metadata
- Paths: `VERSION`, `CHANGELOG.md`
- Required:
  - `VERSION` must contain valid semver
  - `CHANGELOG.md` must contain `Unreleased` and current released version
- Role: source of truth for AIKit release/version discipline

### Knowledge Model
- Paths: `docs/knowledge-model.md`, `schemas/knowledge.model.schema.json`
- Required top-level schema fields: `version`, `entity_types`, `context_pack`
- Role: foundational contract for future knowledge entities, retrieval items and explainable context packs
- Notes:
  - not a runtime data store yet;
  - defines the canonical entity vocabulary for future ingestion, storage and RAG layers.

### Knowledge Source Registry
- Paths: `knowledge/sources/*.json`, `docs/knowledge-source-registry.md`, `schemas/knowledge.source.schema.json`
- Required top-level fields: `version`, `name`, `label`, `source_type`, `description`, `priority`, `enabled_by_default`, `retrieval_roles`, `path_globs`, `profiles`, `domains`, `freshness`, `remote_source`
- Role: canonical registry of knowledge inputs for future ingestion and retrieval
- Notes:
  - separates local vs remote sources;
  - makes source families explicit before storage or RAG implementation.

### Knowledge Store Manifest
- Paths: `knowledge/storage/manifest.json`, `docs/knowledge-storage.md`, `schemas/knowledge.store.schema.json`
- Required top-level fields: `version`, `label`, `description`, `storage_root`, `sqlite_path`, `artifact_cache_dir`, `enabled_sources`, `indexed_entity_types`, `chunking`, `ingestion`
- Role: canonical runtime storage contract for normalized knowledge ingestion
- Notes:
  - defines where local SQLite metadata and enriched artifact cache live;
  - should be updated before changing runtime ingestion behavior.

### Knowledge Retrieval Manifest
- Paths: `knowledge/retrieval/manifest.json`, `docs/retrieval-context-builder.md`, `schemas/knowledge.retrieval.schema.json`
- Required top-level fields: `version`, `label`, `description`, `store_path`, `default_top_k`, `max_constraints`, `scoring`, `intent_rules`, `profile_rules`
- Role: canonical retrieval and ranking policy for explainable context packs
- Notes:
  - defines intent-sensitive source preferences and scoring weights;
  - should be updated before changing runtime context-pack selection logic.

### Knowledge Governance Manifest
- Paths: `knowledge/governance/manifest.json`, `docs/knowledge-governance.md`, `schemas/knowledge.governance.schema.json`
- Required top-level fields: `version`, `label`, `description`, `storage_manifest`, `retrieval_manifest`, `required_workflow_roles`, `required_contract_patterns`, `checks`, `staleness`, `frontend_governance`
- Role: governance and drift-detection policy for knowledge plane consistency
- Notes:
  - defines which drift families are checked and how stale runtime is detected;
  - can include frontend-specific governance requirements for UI kit, design workflows and retrieval coverage;
  - should be updated before changing governance or drift review behavior.

### Runtime Tools Manifest
- Paths: `knowledge/runtime-tools.manifest.json`, `schemas/runtime-tools.manifest.schema.json`
- Required top-level fields: `version`, `default_policy`, `tools`
- Required per tool: `name`, `family`, `kind`, `tool_type`, `category`, `purpose`, `policy`, `requires_repo_root`, `when_to_use`, `outputs`, `writes`, `requires_approval`, `safe_to_auto_run`, `write_scope`, `inputs`, `usage_when`, `blocked_when`
- Semantic fixtures: `docs/fixtures/runtime-tools-fixtures.json`
- Semantic validator: `scripts/validate-runtime-tools-fixtures.py`
- Routing fixtures: `docs/fixtures/tool-family-routing-fixtures.json`
- Routing validator: `scripts/validate-tool-family-routing-fixtures.py`
- Observation enrichment fixtures: `docs/fixtures/observation-enrichment-fixtures.json`
- Observation enrichment validator: `scripts/validate-observation-enrichment-fixtures.py`
- External knowledge fixtures: `docs/fixtures/external-knowledge-surface-fixtures.json`
- External knowledge validator: `scripts/validate-external-knowledge-surfaces.py`
- Domain readiness fixtures: `docs/fixtures/domain-knowledge-readiness-fixtures.json`
- Domain readiness validator: `scripts/validate-domain-knowledge-readiness.py`
- Phase execution fixtures: `docs/phase-execution/P6-execution-plan.json`
- Phase execution validator: `scripts/validate-p6-execution-plan.py`
- Role: machine-readable registry of internal AIKit tools available to CLI agents in Codex, GLM, OpenCode and future runtime workspaces
- Notes:
  - source of truth for `.aikit/runtime-tools.json` generated in adapter bundles;
  - knowledge tools are a first-class family inside this registry, not hidden retrieval implementation detail;
  - current knowledge kinds are `query`, `memory`, `maintenance` and `governance`;
  - semantic fixtures assert that knowledge query/memory/maintenance/governance tools keep their intended safety and write-scope behavior;
  - `tool_type = local-script` requires `command`;
  - `tool_type = mcp-tool` requires `provider`, `runtime_binding`, `availability`, `adapter_support`;
  - MCP-backed tools are runtime-native and should not be modelled as shell commands;
  - MCP fixtures assert that provider-native tools have no shell command and support `claude`, `codex`, `glm`, `opencode`;
  - used by `scripts/run-agent-task.py` to emit task-specific `recommended_tools`;
  - used by `scripts/run-agent-task.py` to emit `knowledge_tooling` as explicit knowledge-family projection for CLI-agents;
  - used by `scripts/run-agent-task.py` to emit `mcp_tooling` as explicit runtime-native MCP/provider projection;
  - `mcp_tooling.provider_matrix` groups provider tools by provider, runtime binding, adapter support, required inputs and blockers;
  - used by `scripts/run-agent-task.py` to emit `tool_family_routing` as explainable routing policy between knowledge, memory, local runtime tools and provider actions;
  - routing fixtures assert expected `route_mode`, `preferred_next_family`, phase decisions, routing signals and recommended tools for representative task classes;
  - used by `scripts/run-agent-task.py` to emit `routing_guidance` as review-oriented explanation layer for ambiguous profile matches, including rerun-ready routing resolution options;
  - used by `scripts/run-agent-task.py` to emit `recommended_tool_invocations` with `ready|needs-input|runtime-native` execution hints;
  - used by `scripts/run-agent-task.py` to emit phased `tool_execution_plan` handoff;
  - used by `scripts/run-agent-task.py` to emit `agent_work_order` as unified CLI-agent handoff;
  - used by `scripts/run-agent-task.py` to execute safe `validate|finalize` phase invocations through `phase_executions`;
  - used by `scripts/run-agent-task.py` to emit `runtime_execution_report` as aggregated execution status for CLI-agent handoff;
  - used by `scripts/run-agent-task.py` to emit `runtime_observation_log` as normalized execution observations and enrichment hints;
  - `runtime_observation_log.memory_enrichment_plan` provides controlled capture recommendations, promotion candidates, retrieval refresh commands and guardrails;
  - used by `scripts/run-agent-task.py` to emit `memory_lifecycle` as canonical-memory archive/pressure state;
  - used by `scripts/run-agent-task.py` to emit `external_knowledge_bridge` as a hybrid contract between canonical repo knowledge and live Figma/GitHub provider surfaces;
  - `external_knowledge_bridge.surface_contracts` and `provider_readiness` describe provider requirements, runtime bindings, blockers and handoff policy;
  - domain readiness fixtures assert whether UI kit and API surface contracts appear in selected context or recommended artifacts for representative tasks;
  - phase execution validators can be registered as runtime validation tools when a roadmap phase needs machine-readable acceptance and validation gates;
  - used by `scripts/run-agent-task.py` to emit `agent_handoff_prompt` as direct continuation prompt for the next CLI-agent session;
  - used by `scripts/run-agent-task.py` to emit `agent_handoff_bundle` with stable artifact paths for next-session pickup;
  - used by `scripts/run-agent-task.py` to emit `resumed_from` when orchestration continues from a saved bundle or runtime journal;
  - used by `scripts/run-agent-task.py` to emit `continuation_state` for resume-aware orchestration and carried completion state;
  - used by `scripts/run-agent-task.py` to emit `suggested_next_runtime_action` as machine-readable next-step recommendation;
  - used by `scripts/run-agent-task.py` to emit `allow_rerun_completed` and enforce resume-aware auto-run skip policy by default;
  - used by `scripts/run-agent-task.py` to emit `session_lineage` for parent/root/depth metadata across continuation runs;
  - keeps Python scripts as internal tooling layer rather than primary human UX;
  - adapter bundles publish `.aikit/mcp-tool-plane.json` as a provider-only projection alongside `.aikit/runtime-tools.json`;
  - should be updated when adding, renaming or changing safety policy for internal runtime tools.

### UI Kit Manifest
- Paths: `profiles/*/uikit.manifest.json`, `docs/uikit-contract.md`, `schemas/uikit.manifest.schema.json`
- Required top-level fields: `version`, `profile`, `label`, `description`, `token_sources`, `primitive_families`, `component_contracts`, `usage_rules`
- Role: profile-scoped structured contract for frontend UI kit knowledge, token sources and reusable primitives
- Notes:
  - foundation for design-aware retrieval and frontend context packs;
  - should be used by design bridge agents before free-form grep across the codebase.

### API Surface Manifest
- Paths: `profiles/*/api-surface.manifest.json`, `docs/api-surface-contract.md`, `schemas/api-surface.manifest.schema.json`
- Required top-level fields: `version`, `profile`, `label`, `description`, `contract_sources`, `surface_families`, `endpoint_contracts`, `usage_rules`
- Role: profile-scoped structured contract for backend API surfaces, auth boundaries and dependency artifacts
- Notes:
  - foundation for backend retrieval and future cross-stack contract reasoning;
  - should be used by backend architects before free-form grep across the codebase.

## Discipline

Если появляется новый structured field:
1. обновляется schema в `schemas/`
2. обновляется `scripts/validate-config.py`
3. затем уже меняются manifests

Если появляется новый manifest type:
1. он должен быть описан здесь
2. у него должна быть schema
3. validator должен уметь его проверять

## Why This Matters

Этот spec layer нужен как foundation для:
- `P2-E4` Adapter Conformance Matrix
- `P2-E3` OpenCode Adapter
- `P1-E2` Canonical Memory Model
- `P3-E1` Workflow Policy Engine
- `KP-E1` Knowledge Model
- `KP-E2` Source Registry
- `KP-E5` Knowledge Storage MVP
- `KP-E6` Retrieval / RAG Context Builder
- `KP-E8` Governance and Drift Detection
- `KP-E3` UI Kit Contract Layer
- `KP-E4` API Surface Contract Layer
