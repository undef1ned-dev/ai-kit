# Backend/Frontend Agent Skills Content Plan

This roadmap analysis closes Phase 15 and proposes the next development direction with an explicit focus on skills content for backend/frontend agents.

## Roadmap Analysis

Completed baselines:
- `Phase 13` closed knowledge runtime maturity: multi-source registry, external docs ingestion, storage readiness, retrieval ranking and memory/RAG promotion.
- `Phase 14` closed multi-runtime productionization: adapter conformance v2, install/update smoke matrix, runtime packet compatibility and GLM/OpenCode practical guides.
- `Phase 15` productized workflow entry: Catalog UX V2, workflow templates, choose-best-agent flow, local docs portal and product governance.

What this means:
- The repository now has enough runtime, docs and workflow infrastructure to spend the next phases on agent quality instead of more scaffolding.
- The highest-leverage gap is skills content depth for backend/frontend agents: examples, decomposition rules, clean architecture boundaries, validation expectations and negative cases.
- Future work should preserve multi-runtime compatibility and local-docs operation.

## Proposed Phases

### Phase 16 — Provider Bridge Runtime

Focus:
turn provider snapshot fixtures into real capture/export usage that can feed backend/frontend agent context.

Skills content:
- provider evidence reading;
- snapshot interpretation;
- handoff prompts.

Validation:
- provider capture fixtures;
- runtime evidence checks.

### Phase 17 — Backend Agent Skills Content Upgrade

Focus:
deepen FastAPI and Django agent skills content around service boundaries, API contracts, data access and clean architecture.

Skills content:
- `new-router`;
- `new-app`;
- `setup-admin`;
- `add-migration`;
- `implement-feature`.

Expected upgrades:
- richer examples for request/response schemas, service boundaries and persistence decisions;
- decomposition guidance for routers, services, repositories, admin and migrations;
- clean architecture rules for dependency direction and API surface stability;
- backend review rubrics that distinguish correctness, maintainability and migration risk.

Validation:
- backend skill content validator;
- API drift validator;
- project evidence validator.

### Phase 18 — Frontend Agent Skills Content Upgrade

Focus:
deepen Vue/Nuxt agent skills content around page/component/composable/store delivery, UI kit reuse and design-to-code context.

Skills content:
- `new-page`;
- `new-component`;
- `new-composable`;
- `new-store`;
- `design-implement`;
- `design-review`.

Expected upgrades:
- richer examples for SSR, hydration, route data, Pinia state ownership and component APIs;
- decomposition guidance for page, component, composable and store boundaries;
- UI kit reuse-first rules tied to live UI kit scanner and component reuse recommender output;
- frontend review rubrics that separate visual fidelity, accessibility, state behavior and maintainability.

Validation:
- frontend skill content validator;
- frontend task workflow validator;
- component reuse validator.

### Phase 19 — Backend Frontend Decomposition And Clean Architecture

Focus:
make decomposition and clean architecture explicit in backend/frontend agent planning, implementation and review skills.

Skills content:
- architecture planning;
- boundary review;
- dependency direction;
- test strategy.

Expected upgrades:
- cross-stack decomposition playbooks;
- frontend/backend boundary examples;
- clean architecture checklists for agents and reviewers;
- fixtures that prove agents choose smaller implementation slices before coding.

Validation:
- decomposition fixtures;
- clean architecture checks;
- cross-stack context checks.

### Phase 20 — Agent Skills Evaluation Governance

Focus:
add repeatable evaluation for backend/frontend skills quality, examples, validators and memory promotion.

Skills content:
- skill examples;
- acceptance rubrics;
- negative cases;
- maintenance checklist.

Expected upgrades:
- fixture-backed quality gates for skill content;
- regression tests for key backend/frontend workflow starts;
- memory promotion rules for reusable agent guidance;
- scorecards for content depth, architectural clarity and validator coverage.

Validation:
- skills evaluation fixtures;
- documentation integrity;
- knowledge drift.

## Recommended Next Move

Start with `Phase 16` if provider capture/export is still the highest dependency for real project evidence. Start with `Phase 17` if the immediate goal is to improve backend agent quality and clean architecture guidance. Start with `Phase 18` if frontend delivery quality is the most urgent user-facing need.
