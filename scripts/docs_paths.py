#!/usr/bin/env python3
"""
Shared docs path registry with compatibility aliases for phased migration.
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

DOC_ALIAS_CANONICAL: dict[str, str] = {
    # Generated and portal surfaces
    "docs_index_html": "docs/generated/index.html",
    "docs_catalog_html": "docs/generated/catalog.html",
    "roadmap_html": "docs/generated/roadmap.html",
    "governance_dashboard_html": "docs/generated/governance-dashboard.html",
    "agent_flow_simulator_html": "docs/generated/agent-flow-simulator.html",
    "agent_flow_simulator_data_json": "docs/generated/agent-flow-simulator-data.json",
    "project_operations_dashboard_html": "docs/generated/project-operations-dashboard.html",
    "product_planning_index_html": "docs/generated/product-planning/index.html",
    "aikit_html_shell_css": "docs/generated/aikit-html-shell.css",
    "local_html_visual_audit_report_json": "docs/generated/local-html-visual-audit-report.json",
    # Source markdown used by integrity checks
    "roadmap_md": "docs/internal/roadmap.md",
    "phase_p12_doc": "docs/phase-execution/P12.md",
    "phase_p12_plan": "docs/phase-execution/P12-execution-plan.json",
    # Local docs portal validator inputs
    "local_docs_portal_fixtures": "docs/fixtures/local-docs-portal-fixtures.json",
    "local_docs_portal_md": "docs/public/local-docs-portal.md",
    # Public and runtime-export markdown surfaces
    "documentation_integrity_md": "docs/public/documentation-integrity.md",
    "agent_workflow_product_governance_md": "docs/public/agent-workflow-product-governance.md",
    "backend_frontend_agent_skills_plan_md": "docs/public/backend-frontend-agent-skills-plan.md",
    "catalog_ux_v2_md": "docs/public/catalog-ux-v2.md",
    "get_started_md": "docs/public/get-started.md",
    "product_story_md": "docs/public/product-story.md",
    "release_center_md": "docs/public/release-center.md",
    "install_matrix_md": "docs/public/install-matrix.md",
    "profiles_summary_md": "docs/public/profiles-summary.md",
    "compatibility_matrix_md": "docs/public/compatibility-matrix.md",
    "runtime_maturity_review_md": "docs/public/runtime-maturity-review.md",
    "marketplace_md": "docs/public/marketplace.md",
    "publishing_workflow_md": "docs/public/publishing-workflow.md",
    "manifest_spec_md": "docs/public/manifest-spec.md",
    "adapter_runtime_execution_md": "docs/public/adapter-runtime-execution.md",
    "adapter_conformance_md": "docs/public/adapter-conformance.md",
    "adapter_conformance_v2_md": "docs/public/adapter-conformance-v2.md",
    "runtime_command_map_md": "docs/public/runtime-command-map.md",
    "runtime_capability_matrix_v2_md": "docs/public/runtime-capability-matrix-v2.md",
    "cli_agent_operating_protocol_md": "docs/public/cli-agent-operating-protocol.md",
    "cli_runtime_continuation_contract_md": "docs/public/cli-runtime-continuation-contract.md",
    "opencode_runtime_guide_md": "docs/public/opencode-runtime-guide.md",
}

DOC_ALIAS_FALLBACKS: dict[str, tuple[str, ...]] = {
    # Generated and portal surfaces
    "docs_index_html": ("docs/index.html", "docs/public/index.html"),
    "docs_catalog_html": ("docs/catalog.html", "docs/public/catalog.html"),
    "roadmap_html": ("docs/roadmap.html",),
    "governance_dashboard_html": ("docs/governance-dashboard.html",),
    "agent_flow_simulator_html": ("docs/agent-flow-simulator.html",),
    "agent_flow_simulator_data_json": ("docs/agent-flow-simulator-data.json",),
    "project_operations_dashboard_html": ("docs/project-operations-dashboard.html",),
    "product_planning_index_html": ("docs/product-planning/index.html",),
    "aikit_html_shell_css": ("docs/aikit-html-shell.css",),
    "local_html_visual_audit_report_json": ("docs/local-html-visual-audit-report.json",),
    # Legacy json fallback kept until generated/fixtures cutover is fully frozen
    "phase_p12_plan": ("docs/internal/phase-execution/P12-execution-plan.json",),
    # Local docs portal validator inputs
    "local_docs_portal_fixtures": ("docs/local-docs-portal-fixtures.json",),
}

ROOT_BUCKETS = ("public", "internal", "fixtures", "generated")
IMMUTABLE_SUBTREES = ("phase-execution", "product-planning")


def _dedupe_keep_order(items: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return tuple(unique)


def _build_doc_aliases() -> dict[str, tuple[str, ...]]:
    aliases: dict[str, tuple[str, ...]] = {}
    for alias, canonical in DOC_ALIAS_CANONICAL.items():
        fallbacks = DOC_ALIAS_FALLBACKS.get(alias, ())
        aliases[alias] = _dedupe_keep_order((canonical, *fallbacks))
    return aliases


DOC_ALIASES: dict[str, tuple[str, ...]] = _build_doc_aliases()

DOC_MARKDOWN_FALLBACK_ALIASES: tuple[str, ...] = tuple(
    sorted(
        alias
        for alias, fallbacks in DOC_ALIAS_FALLBACKS.items()
        if any(candidate.endswith(".md") for candidate in fallbacks)
    )
)


DOC_LEGACY_PATH_ALIASES: dict[str, tuple[str, ...]] = {}
for candidates in DOC_ALIASES.values():
    ordered = _dedupe_keep_order(candidates)
    for candidate in ordered:
        DOC_LEGACY_PATH_ALIASES[candidate] = ordered


def doc_alias_candidates(alias: str) -> tuple[str, ...]:
    candidates = DOC_ALIASES.get(alias)
    if candidates is None:
        raise KeyError(f"Unknown docs alias: {alias}")
    return candidates


def doc_alias_primary(alias: str) -> str:
    primary = DOC_ALIAS_CANONICAL.get(alias)
    if primary is None:
        raise KeyError(f"Unknown docs alias: {alias}")
    return primary


def doc_alias_fallbacks(alias: str) -> tuple[str, ...]:
    if alias not in DOC_ALIAS_CANONICAL:
        raise KeyError(f"Unknown docs alias: {alias}")
    return DOC_ALIAS_FALLBACKS.get(alias, ())


def find_existing_candidates(*relative_candidates: str) -> list[Path]:
    paths: list[Path] = []
    for candidate in relative_candidates:
        path = ROOT / candidate
        if path.exists():
            paths.append(path)
    return paths


def resolve_candidates(*relative_candidates: str) -> Path:
    if not relative_candidates:
        raise ValueError("At least one candidate path is required")
    existing = find_existing_candidates(*relative_candidates)
    if existing:
        return existing[0]
    return ROOT / relative_candidates[0]


def resolve_doc_alias(alias: str) -> Path:
    return resolve_candidates(*doc_alias_candidates(alias))


def doc_relative_candidates(relative_path: str) -> tuple[str, ...]:
    normalized = relative_path.strip()
    if not normalized:
        raise ValueError("relative_path must be non-empty")
    if normalized in DOC_LEGACY_PATH_ALIASES:
        return DOC_LEGACY_PATH_ALIASES[normalized]
    if not normalized.startswith("docs/"):
        return (normalized,)

    tail = normalized[len("docs/") :]
    if not tail:
        return (normalized,)
    if "/" not in tail:
        return _dedupe_keep_order((normalized, *(f"docs/{bucket}/{tail}" for bucket in ROOT_BUCKETS)))

    first, _ = tail.split("/", 1)
    if first in IMMUTABLE_SUBTREES:
        return _dedupe_keep_order((normalized, f"docs/internal/{tail}"))

    return (normalized,)


def resolve_doc_relative(relative_path: str) -> Path:
    return resolve_candidates(*doc_relative_candidates(relative_path))


def repo_relative_path(target: str | Path, source: str | Path | None = None) -> str:
    target_path = Path(target)
    if not target_path.is_absolute():
        target_path = ROOT / target_path
    target_rel = target_path.resolve().relative_to(ROOT).as_posix()

    if source is None:
        return target_rel

    source_path = Path(source)
    if not source_path.is_absolute():
        source_path = ROOT / source_path
    source_path = source_path.resolve()
    start = source_path if source_path.is_dir() else source_path.parent
    return os.path.relpath(target_path, start=start).replace(os.sep, "/")
