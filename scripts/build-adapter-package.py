#!/usr/bin/env python3
"""
Build an experimental runtime package for a selected adapter.

The script packages AIKit core into a runtime-neutral bundle that adapter
targets such as Codex and OpenCode can consume. Claude still uses
scripts/attach.sh as the primary production flow.

Usage:
    python scripts/build-adapter-package.py codex --profile vue-nuxt
    python scripts/build-adapter-package.py opencode --profile vue-nuxt --pack devops
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import re
import sys

from memory_paths import ensure_memory_structure, find_memory_source
from preset_utils import resolve_preset


ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
# Agent Skills standard location read by Codex and OpenCode (Claude Code uses .claude/skills)
NATIVE_SKILLS_DIR = Path(".agents") / "skills"
NATIVE_SKILL_RUNTIMES = {"codex", "opencode"}
NATIVE_ARGUMENTS_PLACEHOLDER = "(задача из запроса пользователя)"
OPENCODE_AGENTS_DIR = Path(".opencode") / "agents"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build runtime-neutral adapter package")
    parser.add_argument("adapter", help="adapter directory name under adapters/")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--profile", help="profile or profile1+profile2")
    selector.add_argument("--preset", help="preset name under presets/")
    parser.add_argument("--pack", action="append", default=[], help="optional pack name, can be repeated")
    parser.add_argument(
        "--target",
        default=str(ROOT / "dist" / "adapters"),
        help="target directory root for generated bundle",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_repo_version() -> str:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    return "unversioned"


def read_pack_compatible_profiles(pack_name: str) -> list[str]:
    pack_json = ROOT / "packs" / pack_name / "pack.json"
    if not pack_json.exists():
        return []
    data = read_json(pack_json)
    compatible = data.get("compatible_profiles", [])
    if not isinstance(compatible, list):
        return []
    return [str(item) for item in compatible if isinstance(item, str) and item.strip()]


def split_frontmatter(text: str) -> tuple[str, str]:
    match = re.match(r"^---[ \t]*\r?\n(.*?\r?\n)---[ \t]*\r?\n?", text, re.DOTALL)
    if not match:
        return "", text
    return match.group(1), text[match.end() :]


def parse_frontmatter(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([\w][\w-]*):\s*(.*)", line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        result[key] = value
    return result


def render_runtime_template(template_text: str, variables: dict[str, str]) -> str:
    result = template_text
    for key, value in variables.items():
        result = result.replace("{{" + key + "}}", value)
    return result


def skill_folders(skills_root: Path) -> list[Path]:
    return sorted(path.parent for path in skills_root.glob("*/SKILL.md"))


def install_skill_folder(source: Path, destination: Path) -> None:
    """Copy a <name>/SKILL.md skill and set name to the folder name."""
    shutil.copytree(source, destination)
    skill_file = destination / "SKILL.md"
    text = skill_file.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^name:.*$", f'name: "{destination.name}"', text, count=1)
    skill_file.write_text(text, encoding="utf-8")


def copy_markdown(src: Path, dst: Path) -> None:
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def runtime_entrypoints(adapter: dict) -> list[dict]:
    return [entry for entry in adapter.get("runtime_entrypoints", []) if isinstance(entry, dict)]


def mirror_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def write_combined_instruction(adapter: dict, profiles: list[str], destination: Path) -> None:
    chunks: list[str] = []
    chunks.append(f"# AIKit Runtime Package — {adapter['label']}\n")
    chunks.append(
        "Этот файл — runtime-neutral сводка AIKit bundle для выбранного adapter.\n"
        "Он не заменяет production flow Claude, а описывает собранный пакет core + adapter.\n"
    )
    chunks.append(f"Runtime: `{adapter['runtime']}`\n")
    chunks.append(f"Status: `{adapter['status']}`\n")
    chunks.append(f"Profiles: `{'+'.join(profiles)}`\n")
    chunks.append("\n---\n\n")
    chunks.append((ROOT / "base" / "CLAUDE.md").read_text(encoding="utf-8"))
    for profile_name in profiles:
        profile_claude = ROOT / "profiles" / profile_name / "CLAUDE.md"
        if profile_claude.exists():
            chunks.append("\n\n---\n\n")
            chunks.append(profile_claude.read_text(encoding="utf-8"))
    destination.write_text("".join(chunks), encoding="utf-8")


def write_claude_instruction_surface(profiles: list[str], destination: Path) -> None:
    chunks: list[str] = []
    base_claude = ROOT / "base" / "CLAUDE.md"
    if base_claude.exists():
        chunks.append(base_claude.read_text(encoding="utf-8"))

    for profile_name in profiles:
        profile_claude = ROOT / "profiles" / profile_name / "CLAUDE.md"
        if profile_claude.exists():
            if chunks:
                chunks.append("\n\n---\n\n")
            chunks.append(profile_claude.read_text(encoding="utf-8"))

    destination.write_text("".join(chunks).rstrip() + "\n", encoding="utf-8")


def merge_settings_documents(paths: list[Path]) -> dict:
    merged: dict = {}
    allow: list[str] = []
    deny: list[str] = []

    for path in paths:
        if not path.exists():
            continue
        payload = read_json(path)
        if not isinstance(payload, dict):
            continue

        merged = merged | payload

        permissions = payload.get("permissions")
        if isinstance(permissions, dict):
            for item in permissions.get("allow", []):
                if isinstance(item, str) and item not in allow:
                    allow.append(item)
            for item in permissions.get("deny", []):
                if isinstance(item, str) and item not in deny:
                    deny.append(item)

    if allow or deny:
        merged["permissions"] = {
            "allow": allow,
            "deny": deny,
        }
    return merged


def write_runtime_specific_files(adapter_name: str, adapter: dict, profiles: list[str], bundle_root: Path) -> None:
    templates_dir = ROOT / "adapters" / adapter_name / "templates"
    if not templates_dir.exists():
        return

    variables = {
        "ADAPTER_LABEL": str(adapter.get("label", "")),
        "ADAPTER_RUNTIME": str(adapter.get("runtime", "")),
        "ADAPTER_STATUS": str(adapter.get("status", "")),
        "PROFILES": "+".join(profiles),
        "MEMORY_PATH": str(adapter.get("memory_path", "")),
    }

    for template_path in sorted(templates_dir.rglob("*.tmpl")):
        rendered = render_runtime_template(template_path.read_text(encoding="utf-8"), variables)
        relative = template_path.relative_to(templates_dir)
        destination = bundle_root / str(relative).replace(".md.tmpl", ".md").replace(".tmpl", "")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")


def write_runtime_entrypoints(
    adapter: dict,
    profiles: list[str],
    bundle_root: Path,
) -> None:
    runtime_root = bundle_root / ".aikit"
    runtime_root.mkdir(parents=True, exist_ok=True)
    entrypoints = runtime_entrypoints(adapter)
    manifest = {
        "adapter": adapter["runtime"],
        "label": adapter["label"],
        "profiles": profiles,
        "memory_path": adapter["memory_path"],
        "entrypoint_style": adapter["entrypoint_style"],
        "entrypoints": entrypoints,
    }
    (runtime_root / "runtime-entrypoints.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    runtime_root_name = f".{adapter['runtime']}"
    for config_root in adapter.get("config_roots", []):
        root_path = bundle_root / config_root
        normalized = config_root.rstrip("/")
        if root_path.is_dir() and Path(normalized).name == runtime_root_name:
            (root_path / "entrypoints.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )


def populate_memory(memory_dir: Path) -> None:
    source_dir = find_memory_source(ROOT)
    if source_dir is not None:
        ensure_memory_structure(memory_dir, ROOT / "base" / "memory" / "INDEX.md")
        for item in sorted(source_dir.iterdir()):
            destination = memory_dir / item.name
            if item.is_dir():
                shutil.copytree(item, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(item, destination)


def write_codex_native_surface(
    adapter: dict,
    profiles: list[str],
    packs: list[str],
    bundle_root: Path,
    agents_dir: Path,
    skills_dir: Path,
    memory_dir: Path,
) -> None:
    if adapter.get("runtime") != "codex":
        return

    codex_root = bundle_root / ".codex"
    codex_root.mkdir(parents=True, exist_ok=True)

    # Agents are converted to .codex/agents/*.toml at install time; skills go to .agents/skills (write_native_skills)
    mirror_tree(agents_dir, codex_root / "agents")

    version_lines = [
        f"profiles={'+'.join(profiles)}",
        f"packs={' '.join(packs)}",
        f"version={read_repo_version()}",
    ]
    (codex_root / ".config-version").write_text("\n".join(version_lines) + "\n", encoding="utf-8")


def frontmatter_document(fields: dict[str, str], body: str) -> str:
    lines = ["---", *(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in fields.items()), "---", ""]
    return "\n".join(lines) + body.lstrip("\n")


def write_native_skills(adapter: dict, bundle_root: Path, skills_dir: Path) -> list[str]:
    """Write skills as <name>/SKILL.md for runtimes that read the Agent Skills standard. Returns written paths."""
    if adapter.get("runtime") not in NATIVE_SKILL_RUNTIMES:
        return []

    native_root = bundle_root / NATIVE_SKILLS_DIR
    native_root.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for source in skill_folders(skills_dir):
        name = source.name
        destination = native_root / name
        shutil.copytree(source, destination)
        raw, body = split_frontmatter((source / "SKILL.md").read_text(encoding="utf-8"))
        # $ARGUMENTS is substituted only by Claude Code; elsewhere the task comes from the user's message
        body = body.replace("$ARGUMENTS", NATIVE_ARGUMENTS_PLACEHOLDER)
        metadata = parse_frontmatter(raw)
        description = metadata.get("description", "").strip()
        if adapter.get("runtime") == "codex" and metadata.get("disable-model-invocation") == "true":
            # Codex counterpart of Claude Code's disable-model-invocation: the skill runs only on explicit $name
            policy_file = destination / "agents" / "openai.yaml"
            policy_file.parent.mkdir(parents=True, exist_ok=True)
            policy_file.write_text("policy:\n  allow_implicit_invocation: false\n", encoding="utf-8")
        if not description:
            raise SystemExit(f"Skill '{name}' has no description — required by Codex and OpenCode")
        if description[0] in ">|":
            raise SystemExit(f"Skill '{name}': description must be a single-line string, not a YAML block scalar")
        # Codex and OpenCode need name and description; name must match the folder (it differs for prefixed skills)
        (destination / "SKILL.md").write_text(
            frontmatter_document({"name": name, "description": description}, body), encoding="utf-8"
        )
        written.append((NATIVE_SKILLS_DIR / name).as_posix())
    return written


def write_opencode_native_agents(adapter: dict, bundle_root: Path, agents_dir: Path) -> list[str]:
    """Write agents as OpenCode subagents. Returns written paths."""
    if adapter.get("runtime") != "opencode":
        return []

    opencode_agents = bundle_root / OPENCODE_AGENTS_DIR
    opencode_agents.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for source in sorted(agents_dir.glob("*.md")):
        raw, body = split_frontmatter(source.read_text(encoding="utf-8"))
        metadata = parse_frontmatter(raw)
        description = metadata.get("description", "").strip() or f"AIKit agent {source.stem}"
        # Claude-specific fields (tools as a string, model aliases) are not valid OpenCode config, so only portable ones are kept
        (opencode_agents / source.name).write_text(
            frontmatter_document({"description": description, "mode": "subagent"}, body), encoding="utf-8"
        )
        written.append((OPENCODE_AGENTS_DIR / source.name).as_posix())
    return written


def write_claude_native_surface(
    adapter: dict,
    profiles: list[str],
    packs: list[str],
    bundle_root: Path,
    agents_dir: Path,
    skills_dir: Path,
) -> list[str]:
    if adapter.get("runtime") != "claude":
        return []

    write_claude_instruction_surface(profiles, bundle_root / "CLAUDE.md")

    claude_root = bundle_root / ".claude"
    claude_root.mkdir(parents=True, exist_ok=True)

    mirror_tree(agents_dir, claude_root / "agents")

    claude_skills = claude_root / "skills"
    mirror_tree(skills_dir, claude_skills)
    native_paths = [(claude_skills / folder.name).relative_to(bundle_root).as_posix() for folder in skill_folders(skills_dir)]

    settings_paths: list[Path] = []
    base_settings = ROOT / "base" / "settings.json"
    if base_settings.exists():
        settings_paths.append(base_settings)
    for profile_name in profiles:
        profile_settings = ROOT / "profiles" / profile_name / "settings.json"
        if profile_settings.exists():
            settings_paths.append(profile_settings)
    for pack_name in packs:
        pack_settings = ROOT / "packs" / pack_name / "settings.json"
        if pack_settings.exists():
            settings_paths.append(pack_settings)

    merged_settings = merge_settings_documents(settings_paths)
    if merged_settings:
        (claude_root / "settings.json").write_text(
            json.dumps(merged_settings, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    version_lines = [
        f"profiles={'+'.join(profiles)}",
        f"packs={' '.join(packs)}",
        f"version={read_repo_version()}",
    ]
    (claude_root / ".config-version").write_text("\n".join(version_lines) + "\n", encoding="utf-8")
    return native_paths


def build_package(
    adapter_name: str,
    profiles_arg: str,
    packs: list[str],
    target_root: Path,
) -> Path:
    adapter_dir = ROOT / "adapters" / adapter_name
    manifest_path = adapter_dir / "adapter.manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Adapter '{adapter_name}' not found at {manifest_path.relative_to(ROOT)}")

    adapter = read_json(manifest_path)
    profiles = [item.strip() for item in profiles_arg.split("+") if item.strip()]
    if not profiles:
        raise SystemExit("At least one profile is required")

    for profile_name in profiles:
        if not (ROOT / "profiles" / profile_name).exists():
            raise SystemExit(f"Unknown profile '{profile_name}'")

    for pack_name in packs:
        if not (ROOT / "packs" / pack_name).exists():
            raise SystemExit(f"Unknown pack '{pack_name}'")
        compatible_profiles = read_pack_compatible_profiles(pack_name)
        # In a multi-profile setup a pack only needs one compatible profile (e.g. a backend-only pack in a web + backend setup)
        if compatible_profiles and not any(profile_name in compatible_profiles for profile_name in profiles):
            raise SystemExit(
                f"Pack '{pack_name}' is not compatible with any of profile(s): {', '.join(profiles)}"
            )

    bundle_root = target_root / adapter_name
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.mkdir(parents=True, exist_ok=True)

    for config_root in adapter.get("config_roots", []):
        if not isinstance(config_root, str) or not config_root.strip():
            continue
        root_path = bundle_root / config_root
        # Treat entries ending with "/" or entries without a dot in the final segment as directories.
        if config_root.endswith("/") or "." not in Path(config_root).name:
            root_path.mkdir(parents=True, exist_ok=True)

    runtime_root = bundle_root / ".aikit"
    agents_dir = runtime_root / "agents"
    skills_dir = runtime_root / "skills"
    canonical_memory_dir = runtime_root / "memory"
    runtime_memory_dir = bundle_root / adapter["memory_path"]
    agents_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)
    canonical_memory_dir.mkdir(parents=True, exist_ok=True)
    runtime_memory_dir.mkdir(parents=True, exist_ok=True)

    # Base agents and skills
    for md in sorted((ROOT / "base" / "agents").glob("*.md")):
        copy_markdown(md, agents_dir / md.name)
    for folder in skill_folders(ROOT / "base" / "skills"):
        install_skill_folder(folder, skills_dir / folder.name)

    # Profile agents and skills; names are unique across the kit (static check)
    for profile_name in profiles:
        profile_agents = ROOT / "profiles" / profile_name / "agents"
        for md in sorted(profile_agents.glob("*.md")):
            copy_markdown(md, agents_dir / md.name)
        for folder in skill_folders(ROOT / "profiles" / profile_name / "skills"):
            install_skill_folder(folder, skills_dir / folder.name)

    # Pack agents and skills
    for pack_name in packs:
        pack_agents = ROOT / "packs" / pack_name / "agents"
        for md in sorted(pack_agents.glob("*.md")):
            copy_markdown(md, agents_dir / md.name)
        for folder in skill_folders(ROOT / "packs" / pack_name / "skills"):
            install_skill_folder(folder, skills_dir / folder.name)

    # Memory seed
    populate_memory(canonical_memory_dir)
    ensure_memory_structure(canonical_memory_dir, ROOT / "base" / "memory" / "INDEX.md")
    if runtime_memory_dir != canonical_memory_dir:
        mirror_tree(canonical_memory_dir, runtime_memory_dir)

    write_combined_instruction(adapter, profiles, bundle_root / "AIKIT.md")
    write_runtime_specific_files(adapter_name, adapter, profiles, bundle_root)
    native_paths = write_claude_native_surface(adapter, profiles, packs, bundle_root, agents_dir, skills_dir)
    write_codex_native_surface(
        adapter,
        profiles,
        packs,
        bundle_root,
        agents_dir,
        skills_dir,
        runtime_memory_dir,
    )
    native_paths += write_native_skills(adapter, bundle_root, skills_dir)
    native_paths += write_opencode_native_agents(adapter, bundle_root, agents_dir)
    write_runtime_entrypoints(adapter, profiles, bundle_root)

    (runtime_root / "adapter.manifest.json").write_text(
        json.dumps(adapter, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    package_manifest = {
        "repo_version": read_repo_version(),
        "adapter": adapter_name,
        "adapter_runtime": adapter["runtime"],
        "adapter_status": adapter["status"],
        "profiles": profiles,
        "packs": packs,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent_count": len(list(agents_dir.glob("*.md"))),
        "skill_count": len(skill_folders(skills_dir)),
        "memory_path": adapter["memory_path"],
        "bundle_root": str(bundle_root.relative_to(ROOT if bundle_root.is_relative_to(ROOT) else bundle_root.parent)),
        "runtime_entrypoint_count": len(runtime_entrypoints(adapter)),
        "codex_native_agent_count": len(list((bundle_root / ".codex" / "agents").glob("*.md"))),
        # Paths outside .aikit/ owned by this package; the installer removes them before the next install
        "native_paths": native_paths,
    }
    (runtime_root / "package.manifest.json").write_text(
        json.dumps(package_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    runtime_notes = [
        f"# {adapter['label']} Package Notes",
        "",
        f"- Runtime: `{adapter['runtime']}`",
        f"- Status: `{adapter['status']}`",
        f"- AIKit version: `{read_repo_version()}`",
        f"- Entrypoint style: `{adapter['entrypoint_style']}`",
        f"- Canonical memory path in this bundle: `{adapter['memory_path']}`",
        "",
        "## Bundle contents",
        "- `AIKIT.md` — combined instruction layer for the selected profiles",
        "- `.aikit/agents/` — packaged agents",
        "- `.aikit/skills/` — packaged skills",
        "- `.aikit/adapter.manifest.json` — adapter contract",
        "- `.aikit/package.manifest.json` — generated package metadata",
        "- `.aikit/runtime-entrypoints.json` — runtime-native launcher contract for this adapter",
        "- `.aikit/profiles.json` — profile contracts: agents by role, specialists, commands",
        "",
        "## Important",
        "- This bundle is an experimental adapter package, not a guarantee of full production integration.",
        "- Claude production flow still uses `scripts/attach.sh` and `scripts/update.sh`.",
    ]
    (bundle_root / "RUNTIME.md").write_text("\n".join(runtime_notes) + "\n", encoding="utf-8")

    return bundle_root


def main() -> int:
    args = parse_args()
    target_root = Path(args.target).resolve()
    profiles_arg = args.profile
    packs = list(args.pack)
    if args.preset:
        preset = resolve_preset(args.preset)
        profiles_arg = preset["profiles_arg"]
        packs = [*preset["packs"], *packs]
    bundle_root = build_package(args.adapter, profiles_arg, packs, target_root)
    print(f"Built adapter package: {bundle_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
