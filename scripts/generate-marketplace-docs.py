#!/usr/bin/env python3
"""
Generate marketplace-facing docs and machine-readable index from curated registry metadata.

Outputs:
- docs/public/marketplace.md
- docs/marketplace.json
- docs/public/publishing-workflow.md
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DOCS = ROOT / "docs" / "public"
MARKETPLACE_MANIFEST = ROOT / "marketplace" / "marketplace.manifest.json"
MARKETPLACE_DOC = PUBLIC_DOCS / "marketplace.md"
MARKETPLACE_JSON = ROOT / "docs" / "marketplace.json"
PUBLISHING_DOC = PUBLIC_DOCS / "publishing-workflow.md"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def profile_visibility_sets() -> tuple[set[str], set[str]]:
    public: set[str] = set()
    deprecated: set[str] = set()
    for path in sorted((ROOT / "profiles").glob("*/profile.manifest.json")):
        data = read_json(path)
        profile = str(data.get("profile", path.parent.name))
        visibility = data.get("visibility", {})
        if not isinstance(visibility, dict):
            visibility = {}
        if visibility.get("scope") == "deprecated-demo-internal" or visibility.get("public_adoption_default") is False:
            deprecated.add(profile)
        else:
            public.add(profile)
    return public, deprecated


def collect_packs() -> list[dict]:
    packs = []
    public_profiles, deprecated_profiles = profile_visibility_sets()
    for path in sorted((ROOT / "packs").glob("*/pack.json")):
        data = read_json(path)
        compatible_profiles = data.get("compatible_profiles", [])
        if not isinstance(compatible_profiles, list):
            compatible_profiles = []
        packs.append(
            {
                "name": data["name"],
                "label": data["label"],
                "description": data["description"],
                "version": data["version"],
                "compatible_profiles": compatible_profiles,
                "public_compatible_profiles": [item for item in compatible_profiles if item in public_profiles],
                "deprecated_compatible_profiles": [item for item in compatible_profiles if item in deprecated_profiles],
                "agents": data.get("agents", []),
                "skills": data.get("skills", []),
                "source": data.get("source", ""),
            }
        )
    return packs


def collect_presets() -> list[dict]:
    presets = []
    for path in sorted((ROOT / "presets").glob("*.json")):
        data = read_json(path)
        presets.append(
            {
                "name": data["name"],
                "label": data["label"],
                "description": data["description"],
                "profiles": data.get("profiles", []),
                "packs": data.get("packs", []),
                "recommended_adapter": data.get("recommended_adapter", ""),
                "lifecycle": data.get("lifecycle", {}),
                "source": data.get("source", ""),
            }
        )
    return presets


def public_presets(presets: list[dict]) -> list[dict]:
    return [preset for preset in presets if preset.get("lifecycle", {}).get("status") != "deprecated"]


def deprecated_presets(presets: list[dict]) -> list[dict]:
    return [preset for preset in presets if preset.get("lifecycle", {}).get("status") == "deprecated"]


def collect_adapters() -> list[dict]:
    adapters = []
    for path in sorted((ROOT / "adapters").glob("*/adapter.manifest.json")):
        data = read_json(path)
        graph = data.get("graph_execution", {})
        adapters.append(
            {
                "name": path.parent.name,
                "label": data["label"],
                "runtime": data["runtime"],
                "status": data["status"],
                "entrypoint_style": data["entrypoint_style"],
                "install_type": data.get("install_type", ""),
                "continuation": bool(data.get("continuation_prompt")),
                "runtime_entrypoints": len(data.get("runtime_entrypoints", [])),
                "graph_execution": graph.get("status", "—") if isinstance(graph, dict) else "—",
            }
        )
    return adapters


def build_index() -> dict:
    manifest = read_json(MARKETPLACE_MANIFEST)
    return {
        "manifest": manifest,
        "packs": collect_packs(),
        "presets": collect_presets(),
        "adapters": collect_adapters(),
    }


def generate_publishing_doc(index: dict) -> str:
    manifest = index["manifest"]
    channels = manifest.get("distribution_channels", [])
    workflows = manifest.get("publishing_workflows", [])
    lines = [
        "# Publishing Workflow",
        "",
        "Этот документ генерируется из marketplace manifest и описывает distribution surface для packs, presets и adapters.",
        "",
        "## Distribution Channels",
        "",
        "| Channel | Kind | Targets | Delivery |",
        "|---------|------|---------|----------|",
    ]
    for channel in channels:
        targets = ", ".join(f"`{item}`" for item in channel.get("targets", [])) or "—"
        lines.append(
            f"| `{channel['name']}` | `{channel['kind']}` | {targets} | {channel['delivery']} |"
        )

    lines.extend(
        [
            "",
            "## Publishing Workflows",
            "",
        ]
    )
    for workflow in workflows:
        lines.extend(
            [
                f"### `{workflow['name']}`",
                "",
                f"- Target kind: `{workflow['target_kind']}`",
                f"- Owner: `{workflow['owner']}`",
                f"- Delivery channels: {', '.join(f'`{item}`' for item in workflow.get('delivery_channels', [])) or '—'}",
                "- Eligibility:",
                *[f"  - {rule}" for rule in workflow.get("eligibility", [])],
                "",
            ]
        )

    lines.extend(
        [
            "## Reading This Surface",
            "",
            "- Start with `docs/public/marketplace.md` to compare packs, presets and adapters.",
            "- Use `docs/public/install-matrix.md` when you need install/update commands for a chosen runtime.",
            "- Use `docs/public/release-center.md` when you need release-state context before adoption.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def generate_markdown(index: dict) -> str:
    manifest = index["manifest"]
    packs = index["packs"]
    presets = public_presets(index["presets"])
    archived_presets = deprecated_presets(index["presets"])
    adapters = index["adapters"]
    archived_pack_profiles = [
        pack
        for pack in packs
        if pack.get("deprecated_compatible_profiles")
    ]

    lines = [
        "# Marketplace",
        "",
        "Этот документ генерируется из curated registry layer AIKit.",
        "Он показывает, как packs, presets и adapters выглядят как project-facing distribution surface.",
        "",
        f"- Registry model: `{manifest['model']}`",
        f"- Status: `{manifest['status']}`",
        "",
        "## Featured",
        "",
        f"- Packs: {', '.join(f'`{item}`' for item in manifest['featured']['packs']) or '—'}",
        f"- Presets: {', '.join(f'`{item}`' for item in manifest['featured']['presets']) or '—'}",
        f"- Adapters: {', '.join(f'`{item}`' for item in manifest['featured']['adapters']) or '—'}",
        "",
        "## Packs",
        "",
        "| Pack | Version | Compatible profiles | Agents | Skills |",
        "|------|---------|---------------------|--------|--------|",
    ]
    for pack in packs:
        lines.append(
            f"| `{pack['name']}` | `{pack['version']}` | {', '.join(f'`{item}`' for item in pack['public_compatible_profiles']) or '—'} | {', '.join(f'`{item}`' for item in pack['agents']) or '—'} | {', '.join(f'`{item}`' for item in pack['skills']) or '—'} |"
        )

    if archived_pack_profiles:
        lines.extend(
            [
                "",
                "## Deprecated Profile Compatibility Archive",
                "",
                "Archived profile compatibility remains source-resolvable, but it is not a supported public/default adoption claim.",
                "",
                "| Pack | Deprecated compatible profiles |",
                "|------|--------------------------------|",
            ]
        )
        for pack in archived_pack_profiles:
            profiles = ", ".join(f"`{item}`" for item in pack["deprecated_compatible_profiles"]) or "—"
            lines.append(f"| `{pack['name']}` | {profiles} |")

    lines.extend(
        [
            "",
            "## Presets",
            "",
            "| Preset | Profiles | Packs | Recommended adapter |",
            "|--------|----------|-------|---------------------|",
        ]
    )
    for preset in presets:
        lines.append(
            f"| `{preset['name']}` | {', '.join(f'`{item}`' for item in preset['profiles']) or '—'} | {', '.join(f'`{item}`' for item in preset['packs']) or '—'} | `{preset['recommended_adapter']}` |"
        )

    if archived_presets:
        lines.extend(
            [
                "",
                "## Deprecated Preset Archive",
                "",
                "These presets stay in source for compatibility, but they are excluded from featured and default public adoption paths.",
                "",
                "| Preset | Profiles | Status | Migration note |",
                "|--------|----------|--------|----------------|",
            ]
        )
        for preset in archived_presets:
            lifecycle = preset.get("lifecycle", {})
            profiles = ", ".join(f"`{item}`" for item in preset["profiles"]) or "—"
            note = lifecycle.get("replacement_guidance", "create a project-specific profile before new adoption")
            lines.append(f"| `{preset['name']}` | {profiles} | `deprecated` | {note} |")

    lines.extend(
        [
            "",
            "## Runtime Adapters",
            "",
            "| Adapter | Runtime | Status | Install | Continuation | Runtime entrypoints | Graph execution |",
            "|---------|---------|--------|---------|--------------|---------------------|-----------------|",
        ]
    )
    for adapter in adapters:
        install = f"`{adapter['install_type']}`" if adapter["install_type"] else "—"
        continuation = "`yes`" if adapter["continuation"] else "`no`"
        lines.append(
            f"| `{adapter['name']}` | `{adapter['runtime']}` | `{adapter['status']}` | {install} | {continuation} | `{adapter['runtime_entrypoints']}` | `{adapter['graph_execution']}` |"
        )

    lines.extend(
        [
        "",
        "## Publishing Rules",
        "",
        *[f"- {rule}" for rule in manifest.get("publishing_rules", [])],
        "",
        "## Distribution Channels",
        "",
        *[
            f"- `{channel['name']}` (`{channel['kind']}`) → {channel['delivery']}"
            for channel in manifest.get("distribution_channels", [])
        ],
        "",
        "## Why this exists",
        "",
        "Marketplace layer не делает AIKit публичным app store или live registry прямо сейчас.",
        "Но он даёт curated distribution surface, на который уже можно опираться для docs, install choice и bundle comparison без погружения во внутренние maintainer workflows.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    index = build_index()
    MARKETPLACE_JSON.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MARKETPLACE_DOC.write_text(generate_markdown(index), encoding="utf-8")
    PUBLISHING_DOC.write_text(generate_publishing_doc(index), encoding="utf-8")
    print(f"Updated {MARKETPLACE_JSON}")
    print(f"Updated {MARKETPLACE_DOC}")
    print(f"Updated {PUBLISHING_DOC}")


if __name__ == "__main__":
    main()
