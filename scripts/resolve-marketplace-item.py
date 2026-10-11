#!/usr/bin/env python3
"""
Resolve a marketplace item and explain how it is distributed inside AIKit.

Usage:
    python3 scripts/resolve-marketplace-item.py pack quality
    python3 scripts/resolve-marketplace-item.py preset frontend-team --json
    python3 scripts/resolve-marketplace-item.py adapter codex
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE_MANIFEST = ROOT / "marketplace" / "marketplace.manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_marketplace() -> dict:
    return read_json(MARKETPLACE_MANIFEST)


def load_item(kind: str, name: str) -> dict:
    if kind == "pack":
        path = ROOT / "packs" / name / "pack.json"
    elif kind == "preset":
        path = ROOT / "presets" / f"{name}.json"
    elif kind == "adapter":
        path = ROOT / "adapters" / name / "adapter.manifest.json"
    else:
        raise SystemExit(f"Unsupported kind: {kind}")

    if not path.exists():
        raise SystemExit(f"{kind} '{name}' not found")
    data = read_json(path)
    data["_path"] = str(path.relative_to(ROOT))
    return data


def matching_workflows(manifest: dict, kind: str) -> list[dict]:
    return [workflow for workflow in manifest.get("publishing_workflows", []) if workflow.get("target_kind") == kind]


def render_text(kind: str, name: str, item: dict, manifest: dict) -> str:
    lines = [
        f"# Marketplace Item — {kind}:{name}",
        "",
        f"- Source: `{item['_path']}`",
    ]
    if "label" in item:
        lines.append(f"- Label: `{item['label']}`")
    if "description" in item:
        lines.append(f"- Description: {item['description']}")
    if kind == "preset":
        lines.append(f"- Profiles: {', '.join(f'`{p}`' for p in item.get('profiles', [])) or '—'}")
        lines.append(f"- Packs: {', '.join(f'`{p}`' for p in item.get('packs', [])) or '—'}")
        lines.append(f"- Recommended adapter: `{item.get('recommended_adapter', '—')}`")
    elif kind == "pack":
        lines.append(f"- Compatible profiles: {', '.join(f'`{p}`' for p in item.get('compatible_profiles', [])) or '—'}")
        lines.append(f"- Skills: {', '.join(f'`{s}`' for s in item.get('skills', [])) or '—'}")
    elif kind == "adapter":
        lines.append(f"- Runtime: `{item.get('runtime', '')}`")
        lines.append(f"- Status: `{item.get('status', '')}`")
        lines.append(f"- Install type: `{item.get('install_type', '—')}`")

    lines.extend(["", "## Publishing workflows", ""])
    workflows = matching_workflows(manifest, kind)
    if not workflows:
        lines.append("- No publishing workflows declared.")
        return "\n".join(lines) + "\n"

    for workflow in workflows:
        lines.append(f"### `{workflow['name']}`")
        lines.append("")
        lines.append(f"- Owner: `{workflow['owner']}`")
        lines.append(f"- Delivery channels: {', '.join(f'`{c}`' for c in workflow.get('delivery_channels', [])) or '—'}")
        lines.append("- Eligibility:")
        for rule in workflow.get("eligibility", []):
            lines.append(f"  - {rule}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve an AIKit marketplace item")
    parser.add_argument("kind", choices=["pack", "preset", "adapter"])
    parser.add_argument("name")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_marketplace()
    item = load_item(args.kind, args.name)
    payload = {
        "kind": args.kind,
        "name": args.name,
        "item": item,
        "workflows": matching_workflows(manifest, args.kind),
        "distribution_channels": manifest.get("distribution_channels", []),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(args.kind, args.name, item, manifest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
