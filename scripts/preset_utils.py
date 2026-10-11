#!/usr/bin/env python3
"""
Helpers for AIKit distribution presets.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PRESETS_DIR = ROOT / "presets"


def list_presets() -> list[dict[str, Any]]:
    presets: list[dict[str, Any]] = []
    for path in sorted(PRESETS_DIR.glob("*.json")):
        presets.append(json.loads(path.read_text(encoding="utf-8")))
    return presets


def load_preset(name: str) -> dict[str, Any]:
    path = PRESETS_DIR / f"{name}.json"
    if not path.exists():
        raise SystemExit(f"Unknown preset '{name}'")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_preset(name: str) -> dict[str, Any]:
    preset = load_preset(name)
    profiles = [str(item) for item in preset.get("profiles", [])]
    packs = [str(item) for item in preset.get("packs", [])]
    return {
        "name": preset.get("name", name),
        "label": preset.get("label", name),
        "description": preset.get("description", ""),
        "profiles": profiles,
        "profiles_arg": "+".join(profiles),
        "packs": packs,
        "recommended_adapter": str(preset.get("recommended_adapter", "")),
        "source": str(preset.get("source", "")),
    }
