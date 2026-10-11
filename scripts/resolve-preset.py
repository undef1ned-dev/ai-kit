#!/usr/bin/env python3
"""
Resolve an AIKit preset into profiles/packs for humans and tooling.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from preset_utils import list_presets, resolve_preset


ROOT = Path(__file__).resolve().parent.parent
ADAPTERS_DIR = ROOT / "adapters"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve AIKit preset bundles")
    parser.add_argument("preset", nargs="?", help="preset name under presets/")
    parser.add_argument("--adapter", help="limit command suggestions to one runtime adapter")
    parser.add_argument("--json", action="store_true", help="print JSON payload")
    parser.add_argument("--list", action="store_true", help="list available presets")
    return parser.parse_args()


def active_runtime_adapters() -> list[str]:
    adapters: list[str] = []
    for path in sorted(ADAPTERS_DIR.glob("*/adapter.manifest.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        runtime = str(data.get("runtime", path.parent.name))
        if runtime == "claude":
            continue
        if data.get("status") == "active" and data.get("install_script"):
            adapters.append(runtime)
    return adapters


def distribution_commands(preset_name: str, adapter: str | None = None) -> dict[str, object]:
    adapters = active_runtime_adapters()
    if adapter:
        if adapter not in adapters:
            raise SystemExit(f"Adapter '{adapter}' does not support active preset install flow")
        adapters = [adapter]

    runtime_commands = {
        runtime: {
            "inspect": f"/aikit-install-update inspect --preset {preset_name} --adapter {runtime}",
            "build": f"/aikit-install-update build {runtime} --preset {preset_name} --target /tmp/aikit-{runtime}-build",
            "install": f"/aikit-runtime-workspace {runtime} --preset {preset_name} --workspace /tmp/aikit-{runtime}",
            "update": f"/aikit-runtime-workspace {runtime} --preset {preset_name} --workspace /tmp/aikit-{runtime} --operation update",
            "dry_run": f"/aikit-runtime-workspace {runtime} --preset {preset_name} --workspace /tmp/aikit-{runtime} --dry-run",
        }
        for runtime in adapters
    }
    return {
        "claude": {
            "attach": f"bash .aikit-config/scripts/attach.sh --preset {preset_name}",
            "update": "bash .aikit-config/scripts/update.sh",
        },
        "runtime_adapters": runtime_commands,
    }


def main() -> int:
    args = parse_args()
    if args.list:
        presets = list_presets()
        if args.json:
            print(json.dumps(presets, ensure_ascii=False, indent=2))
        else:
            print("Available presets")
            print("=================")
            for preset in presets:
                print(f"- {preset['name']}: {preset['label']}")
                print(f"  profiles: {'+'.join(preset.get('profiles', []))}")
                print(f"  packs: {', '.join(preset.get('packs', [])) or '—'}")
                print(f"  recommended adapter: {preset.get('recommended_adapter', '—')}")
        return 0

    if not args.preset:
        raise SystemExit("Preset name is required unless --list is used")

    preset = resolve_preset(args.preset)
    commands = distribution_commands(preset["name"], args.adapter)
    payload = {**preset, "commands": commands}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Preset resolution")
        print("=================")
        print(f"Preset: {preset['name']}")
        print(f"Label: {preset['label']}")
        print(f"Description: {preset['description']}")
        print(f"Profiles: {preset['profiles_arg']}")
        print(f"Packs: {', '.join(preset['packs']) or '—'}")
        print(f"Recommended adapter: {preset['recommended_adapter'] or '—'}")
        print("")
        print("Distribution commands")
        print("=====================")
        print(f"Claude attach: {commands['claude']['attach']}")
        print(f"Claude update: {commands['claude']['update']}")
        for runtime, runtime_commands in commands["runtime_adapters"].items():
            print(f"{runtime} inspect: {runtime_commands['inspect']}")
            print(f"{runtime} build: {runtime_commands['build']}")
            print(f"{runtime} install: {runtime_commands['install']}")
            print(f"{runtime} update: {runtime_commands['update']}")
            print(f"{runtime} dry-run: {runtime_commands['dry_run']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
