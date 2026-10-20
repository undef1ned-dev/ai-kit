#!/usr/bin/env python3
"""
Update an installed AIKit adapter workspace by resyncing the selected bundle.

Usage:
    python scripts/update-adapter-package.py codex --profile vue-nuxt --workspace /tmp/my-codex-workspace
    python scripts/update-adapter-package.py opencode --preset frontend-team --workspace /tmp/my-opencode-workspace
"""

from __future__ import annotations

import argparse
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_install_module():
    path = ROOT / "scripts" / "install-adapter-package.py"
    spec = importlib.util.spec_from_file_location("aikit_install_adapter_package", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Unable to load installer module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update an installed AIKit adapter workspace")
    parser.add_argument("adapter", help="adapter directory name under adapters/")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--profile", help="profile or profile1+profile2")
    selector.add_argument("--preset", help="preset name under presets/")
    parser.add_argument("--pack", action="append", default=[], help="optional pack name, can be repeated")
    parser.add_argument(
        "--workspace",
        required=True,
        help="target workspace where runtime files should be updated",
    )
    return parser.parse_args()


def write_update_summary(adapter: dict, workspace: Path, profiles_arg: str, packs: list[str]) -> None:
    summary = [
        f"# AIKit Update Summary — {adapter['label']}",
        "",
        f"- Runtime: `{adapter['runtime']}`",
        f"- Status: `{adapter['status']}`",
        f"- Updated at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Workspace: `{workspace}`",
        f"- Profiles: `{profiles_arg}`",
        f"- Packs: `{', '.join(packs) if packs else '—'}`",
        "",
        "## Next steps",
        "- Проверь `.aikit/runtime-entrypoints.json` и runtime-local `entrypoints.json`.",
        "- При необходимости повторно прогоняй install/update тем же selection contract.",
    ]
    (workspace / ".aikit" / "UPDATE.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    installer = load_install_module()
    profiles_arg, packs = installer.resolve_profiles_and_packs(args.profile, args.preset, list(args.pack))
    adapter = installer.install_package(args.adapter, profiles_arg, packs, workspace)
    write_update_summary(adapter, workspace, profiles_arg, packs)
    print(f"Updated adapter package '{args.adapter}' in {workspace}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
