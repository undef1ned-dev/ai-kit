#!/usr/bin/env python3
"""
Build an experimental runtime package for a selected adapter.

The script packages AIKit core into a runtime-neutral bundle that adapter
targets such as Codex and OpenCode can consume. Claude still uses
scripts/attach.sh as the primary production flow.

Usage:
    python scripts/build-adapter-package.py codex --profile vue-nuxt
    python scripts/build-adapter-package.py opencode --profile python-fastapi --pack devops
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
from docs_paths import resolve_doc_alias
from preset_utils import resolve_preset


ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "base" / "skills" / "templates"
VERSION_FILE = ROOT / "VERSION"
RUNTIME_OPERATING_PROTOCOL = resolve_doc_alias("cli_agent_operating_protocol_md")
RUNTIME_CONTINUATION_CONTRACT = resolve_doc_alias("cli_runtime_continuation_contract_md")
RUNTIME_TOOLS_MANIFEST = ROOT / "knowledge" / "runtime-tools.manifest.json"
COMMAND_SURFACE_FIXTURE = ROOT / "docs" / "fixtures" / "command-surface-inventory-fixtures.json"
PACKAGE_MODE_CONSUMER = "consumer"
PACKAGE_MODE_MAINTAINER = "maintainer"
MAINTAINER_PROMPT_NAME = "CONTINUE_AIKIT_MAINTAINER.md"


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
    parser.add_argument(
        "--mode",
        choices=[PACKAGE_MODE_CONSUMER, PACKAGE_MODE_MAINTAINER],
        default=PACKAGE_MODE_CONSUMER,
        help="package mode. consumer excludes maintainer-local command surfaces; maintainer preserves them",
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


def parse_body_blocks(body: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    current_key: str | None = None
    buf: list[str] = []

    for line in body.splitlines():
        match = re.match(r"^\[([A-Z][A-Z0-9_]*)\]\s*$", line)
        if match:
            if current_key is not None:
                blocks[current_key] = "\n".join(buf).strip()
            current_key = match.group(1)
            buf = []
            continue
        buf.append(line)

    if current_key is not None:
        blocks[current_key] = "\n".join(buf).strip()

    return blocks


def expand_template(template_text: str, inline_vars: dict[str, str], blocks: dict[str, str]) -> str:
    result = template_text
    for key, value in inline_vars.items():
        result = result.replace("{{" + key + "}}", value)

    def replace_block(match: re.Match[str]) -> str:
        key = match.group(1)
        value = blocks.get(key, "").strip()
        return (value + "\n") if value else ""

    result = re.sub(r"\{\{([A-Z][A-Z0-9_]*)\}\}\n?", replace_block, result)
    return re.sub(r"\n{3,}", "\n\n", result)


def render_runtime_template(template_text: str, variables: dict[str, str]) -> str:
    result = template_text
    for key, value in variables.items():
        result = result.replace("{{" + key + "}}", value)
    return result


def expand_skill_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    raw, body = split_frontmatter(text)
    fm = parse_frontmatter(raw)
    template_name = fm.get("template", "").strip()
    if not template_name:
        return text

    template_path = TEMPLATES_DIR / f"{template_name}.md.tmpl"
    if not template_path.exists():
        return text

    inline_vars = {
        key[5:]: value
        for key, value in fm.items()
        if key.startswith("tvar_")
    }
    inline_vars.setdefault("PROFILE", fm.get("profile", ""))
    inline_vars.setdefault("EXAMPLE_PROMPT", fm.get("example_prompt", ""))
    blocks = parse_body_blocks(body)
    return expand_template(template_path.read_text(encoding="utf-8"), inline_vars, blocks)


def profile_prefix(profile_name: str) -> str:
    return re.sub(r"-[a-z0-9]+$", "", profile_name.replace("python-", ""))


def find_conflicts(profile_names: list[str], subdir: str) -> set[str]:
    counts: dict[str, int] = {}
    for profile_name in profile_names:
        directory = ROOT / "profiles" / profile_name / subdir
        if not directory.exists():
            continue
        for md in directory.glob("*.md"):
            counts[md.name] = counts.get(md.name, 0) + 1
    return {name for name, count in counts.items() if count > 1}


def copy_markdown(src: Path, dst: Path) -> None:
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def command_surface_scopes() -> dict[str, str]:
    if not COMMAND_SURFACE_FIXTURE.exists():
        return {}
    data = read_json(COMMAND_SURFACE_FIXTURE)
    scopes: dict[str, str] = {}
    root_commands = data.get("root_commands", [])
    if not isinstance(root_commands, list):
        return scopes
    for item in root_commands:
        if not isinstance(item, dict):
            continue
        path_text = str(item.get("path", "")).strip()
        scope = str(item.get("scope", "")).strip()
        if path_text and scope:
            scopes[path_text] = scope
    return scopes


def include_source_command_in_package(command_path: Path, package_mode: str) -> bool:
    if package_mode == PACKAGE_MODE_MAINTAINER:
        return True
    try:
        rel_path = command_path.relative_to(ROOT).as_posix()
    except ValueError:
        return False
    return command_surface_scopes().get(rel_path) == "user-facing"


def include_template_in_package(destination_rel: str, package_mode: str) -> bool:
    if package_mode == PACKAGE_MODE_MAINTAINER:
        return True
    normalized = destination_rel.strip("/")
    if Path(normalized).name == MAINTAINER_PROMPT_NAME:
        return False
    if normalized.startswith(".codex/commands/"):
        return command_surface_scopes().get(normalized) == "user-facing"
    return True


def runtime_entrypoints_for_mode(adapter: dict, package_mode: str) -> list[dict]:
    entrypoints = [entry for entry in adapter.get("runtime_entrypoints", []) if isinstance(entry, dict)]
    if package_mode == PACKAGE_MODE_MAINTAINER:
        return entrypoints
    return [
        entry
        for entry in entrypoints
        if entry.get("name") != "continue-maintainer"
        and MAINTAINER_PROMPT_NAME not in str(entry.get("path", ""))
    ]


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
    chunks.append(
        "\n## Runtime operating protocol\n\n"
        "Пользователь общается с runtime CLI обычным языком. "
        "Агент сам выбирает profile, workflow, skills, memory и внутренние Python tools.\n\n"
        "Если в bundle есть `.aikit/runtime-operating-protocol.md`, прочитай его перед запуском orchestration tasks.\n"
    )
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
    mcp_servers: dict = {}

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

        servers = payload.get("mcpServers")
        if isinstance(servers, dict):
            mcp_servers.update(servers)

    if allow or deny:
        merged["permissions"] = {
            "allow": allow,
            "deny": deny,
        }
    if mcp_servers:
        merged["mcpServers"] = mcp_servers
    return merged


def write_runtime_operating_protocol(adapter: dict, profiles: list[str], bundle_root: Path) -> None:
    runtime_root = bundle_root / ".aikit"
    runtime_root.mkdir(parents=True, exist_ok=True)
    protocol_path = runtime_root / "runtime-operating-protocol.md"
    if not RUNTIME_OPERATING_PROTOCOL.exists():
        return

    header = [
        f"# Runtime Operating Protocol — {adapter['label']}",
        "",
        f"- Runtime: `{adapter['runtime']}`",
        f"- Status: `{adapter['status']}`",
        f"- Profiles: `{'+'.join(profiles)}`",
        "",
        "---",
        "",
    ]
    protocol_path.write_text(
        "\n".join(header) + RUNTIME_OPERATING_PROTOCOL.read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def write_runtime_continuation_contract(adapter: dict, profiles: list[str], bundle_root: Path) -> None:
    runtime_root = bundle_root / ".aikit"
    runtime_root.mkdir(parents=True, exist_ok=True)
    contract_path = runtime_root / "runtime-continuation-contract.md"
    if not RUNTIME_CONTINUATION_CONTRACT.exists():
        return

    header = [
        f"# Runtime Continuation Contract — {adapter['label']}",
        "",
        f"- Runtime: `{adapter['runtime']}`",
        f"- Status: `{adapter['status']}`",
        f"- Profiles: `{'+'.join(profiles)}`",
        "",
        "---",
        "",
    ]
    contract_path.write_text(
        "\n".join(header) + RUNTIME_CONTINUATION_CONTRACT.read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def write_runtime_tools_registry(adapter: dict, profiles: list[str], bundle_root: Path) -> None:
    runtime_root = bundle_root / ".aikit"
    runtime_root.mkdir(parents=True, exist_ok=True)
    if not RUNTIME_TOOLS_MANIFEST.exists():
        return

    data = read_json(RUNTIME_TOOLS_MANIFEST)
    data["adapter"] = adapter["runtime"]
    data["adapter_status"] = adapter["status"]
    data["profiles"] = profiles
    (runtime_root / "runtime-tools.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_mcp_tool_plane(adapter: dict, profiles: list[str]) -> dict[str, object]:
    data = read_json(RUNTIME_TOOLS_MANIFEST)
    adapter_runtime = str(adapter.get("runtime", "")).strip()
    mcp_tools = [
        tool
        for tool in data.get("tools", [])
        if isinstance(tool, dict)
        and str(tool.get("tool_type", "")).strip() == "mcp-tool"
        and adapter_runtime in [str(item).strip() for item in tool.get("adapter_support", [])]
    ]
    providers: dict[str, dict[str, object]] = {}
    for tool in mcp_tools:
        provider = str(tool.get("provider", "")).strip() or "unknown"
        entry = providers.setdefault(
            provider,
            {
                "provider": provider,
                "runtime_bindings": [],
                "tools": [],
                "blocked_when": [],
                "required_inputs": [],
            },
        )
        entry["tools"].append(
            {
                "name": tool.get("name"),
                "family": tool.get("family"),
                "kind": tool.get("kind"),
                "category": tool.get("category"),
                "runtime_binding": tool.get("runtime_binding"),
                "availability": tool.get("availability"),
                "requires_approval": tool.get("requires_approval"),
                "write_scope": tool.get("write_scope"),
                "command": [],
            }
        )
        runtime_binding = str(tool.get("runtime_binding", "")).strip()
        if runtime_binding and runtime_binding not in entry["runtime_bindings"]:
            entry["runtime_bindings"].append(runtime_binding)
        for blocked in tool.get("blocked_when", []):
            if blocked not in entry["blocked_when"]:
                entry["blocked_when"].append(blocked)
        for input_name in tool.get("inputs", []):
            if input_name not in entry["required_inputs"]:
                entry["required_inputs"].append(input_name)

    return {
        "adapter": adapter_runtime,
        "adapter_status": adapter.get("status", ""),
        "profiles": profiles,
        "source_ref": str(RUNTIME_TOOLS_MANIFEST.relative_to(ROOT)),
        "policy": "runtime-native-mcp",
        "requirements": [
            "MCP tools must be invoked through the runtime provider layer.",
            "MCP tools must not be executed as local shell commands.",
            "Canonical AIKit knowledge should be checked before provider lookups when both are relevant.",
        ],
        "providers": sorted(providers.values(), key=lambda item: str(item.get("provider", ""))),
    }


def write_mcp_tool_plane(adapter: dict, profiles: list[str], bundle_root: Path) -> None:
    runtime_root = bundle_root / ".aikit"
    runtime_root.mkdir(parents=True, exist_ok=True)
    if not RUNTIME_TOOLS_MANIFEST.exists():
        return
    (runtime_root / "mcp-tool-plane.json").write_text(
        json.dumps(build_mcp_tool_plane(adapter, profiles), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_runtime_specific_files(
    adapter_name: str,
    adapter: dict,
    profiles: list[str],
    bundle_root: Path,
    package_mode: str = PACKAGE_MODE_CONSUMER,
) -> None:
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
        destination_rel = str(relative).replace(".md.tmpl", ".md").replace(".tmpl", "")
        if not include_template_in_package(destination_rel, package_mode):
            continue
        destination = bundle_root / destination_rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")


def write_runtime_entrypoints(
    adapter: dict,
    profiles: list[str],
    bundle_root: Path,
    package_mode: str = PACKAGE_MODE_CONSUMER,
) -> None:
    runtime_root = bundle_root / ".aikit"
    runtime_root.mkdir(parents=True, exist_ok=True)
    entrypoints = runtime_entrypoints_for_mode(adapter, package_mode)
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


def write_runtime_graph(adapter: dict, profiles: list[str], bundle_root: Path) -> None:
    runtime_root = bundle_root / ".aikit"
    runtime_root.mkdir(parents=True, exist_ok=True)
    recipes: list[dict[str, object]] = []
    for profile_name in profiles:
        workflow_path = ROOT / "profiles" / profile_name / "workflow.manifest.json"
        if not workflow_path.exists():
            continue
        workflow = read_json(workflow_path)
        recipes.append(
            {
                "profile": profile_name,
                "default_recipe": workflow.get("default_recipe", ""),
                "recipes": workflow.get("recipes", []),
            }
        )

    graph_config = adapter.get("graph_execution", {})
    graph_manifest = {
        "adapter": adapter["runtime"],
        "label": adapter["label"],
        "profiles": profiles,
        "graph_execution": graph_config,
        "workflow_sets": recipes,
    }

    shared_artifact = graph_config.get("shared_artifact")
    if isinstance(shared_artifact, str) and shared_artifact.strip():
        shared_path = bundle_root / shared_artifact
        shared_path.parent.mkdir(parents=True, exist_ok=True)
        shared_path.write_text(json.dumps(graph_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    runtime_artifact = graph_config.get("runtime_artifact")
    if isinstance(runtime_artifact, str) and runtime_artifact.strip():
        runtime_path = bundle_root / runtime_artifact
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_path.write_text(json.dumps(graph_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    package_mode: str = PACKAGE_MODE_CONSUMER,
) -> None:
    if adapter.get("runtime") != "codex":
        return

    codex_root = bundle_root / ".codex"
    codex_root.mkdir(parents=True, exist_ok=True)

    mirror_tree(agents_dir, codex_root / "agents")
    mirror_tree(skills_dir, codex_root / "skills")
    mirror_tree(memory_dir, codex_root / "memory")

    commands_dir = codex_root / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    for skill in sorted(skills_dir.glob("*.md")):
        copy_markdown(skill, commands_dir / skill.name)

    source_commands = ROOT / ".codex" / "commands"
    if source_commands.exists():
        for command in sorted(source_commands.glob("*.md")):
            if not include_source_command_in_package(command, package_mode):
                continue
            copy_markdown(command, commands_dir / command.name)

    version_lines = [
        f"profiles={'+'.join(profiles)}",
        f"packs={' '.join(packs)}",
        f"version={read_repo_version()}",
        f"package_mode={package_mode}",
    ]
    (codex_root / ".config-version").write_text("\n".join(version_lines) + "\n", encoding="utf-8")


def write_claude_native_surface(
    adapter: dict,
    profiles: list[str],
    packs: list[str],
    bundle_root: Path,
    agents_dir: Path,
    skills_dir: Path,
) -> None:
    if adapter.get("runtime") != "claude":
        return

    write_claude_instruction_surface(profiles, bundle_root / "CLAUDE.md")

    claude_root = bundle_root / ".claude"
    claude_root.mkdir(parents=True, exist_ok=True)

    mirror_tree(agents_dir, claude_root / "agents")

    commands_dir = claude_root / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    for skill in sorted(skills_dir.glob("*.md")):
        copy_markdown(skill, commands_dir / skill.name)

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


def build_package(
    adapter_name: str,
    profiles_arg: str,
    packs: list[str],
    target_root: Path,
    package_mode: str = PACKAGE_MODE_CONSUMER,
) -> Path:
    if package_mode not in {PACKAGE_MODE_CONSUMER, PACKAGE_MODE_MAINTAINER}:
        raise SystemExit(f"Unknown package mode '{package_mode}'")

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
        if compatible_profiles:
            incompatible = [profile_name for profile_name in profiles if profile_name not in compatible_profiles]
            if incompatible:
                raise SystemExit(
                    f"Pack '{pack_name}' is not compatible with profile(s): {', '.join(incompatible)}"
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
    for md in sorted((ROOT / "base" / "skills").glob("*.md")):
        (skills_dir / md.name).write_text(expand_skill_text(md), encoding="utf-8")

    # Profile agents and skills with conflict-safe names
    agent_conflicts = find_conflicts(profiles, "agents")
    skill_conflicts = find_conflicts(profiles, "skills")
    for profile_name in profiles:
        prefix = profile_prefix(profile_name)

        profile_agents = ROOT / "profiles" / profile_name / "agents"
        for md in sorted(profile_agents.glob("*.md")):
            dst_name = f"{prefix}-{md.name}" if md.name in agent_conflicts else md.name
            copy_markdown(md, agents_dir / dst_name)

        profile_skills = ROOT / "profiles" / profile_name / "skills"
        for md in sorted(profile_skills.glob("*.md")):
            dst_name = f"{prefix}-{md.name}" if md.name in skill_conflicts else md.name
            (skills_dir / dst_name).write_text(expand_skill_text(md), encoding="utf-8")

    # Pack agents and skills
    for pack_name in packs:
        pack_agents = ROOT / "packs" / pack_name / "agents"
        for md in sorted(pack_agents.glob("*.md")):
            copy_markdown(md, agents_dir / md.name)
        pack_skills = ROOT / "packs" / pack_name / "skills"
        for md in sorted(pack_skills.glob("*.md")):
            (skills_dir / md.name).write_text(expand_skill_text(md), encoding="utf-8")

    # Memory seed
    populate_memory(canonical_memory_dir)
    ensure_memory_structure(canonical_memory_dir, ROOT / "base" / "memory" / "INDEX.md")
    if runtime_memory_dir != canonical_memory_dir:
        mirror_tree(canonical_memory_dir, runtime_memory_dir)

    write_combined_instruction(adapter, profiles, bundle_root / "AIKIT.md")
    write_runtime_operating_protocol(adapter, profiles, bundle_root)
    write_runtime_continuation_contract(adapter, profiles, bundle_root)
    write_runtime_tools_registry(adapter, profiles, bundle_root)
    write_mcp_tool_plane(adapter, profiles, bundle_root)
    write_runtime_specific_files(adapter_name, adapter, profiles, bundle_root, package_mode)
    write_claude_native_surface(adapter, profiles, packs, bundle_root, agents_dir, skills_dir)
    write_codex_native_surface(
        adapter,
        profiles,
        packs,
        bundle_root,
        agents_dir,
        skills_dir,
        runtime_memory_dir,
        package_mode,
    )
    write_runtime_entrypoints(adapter, profiles, bundle_root, package_mode)
    write_runtime_graph(adapter, profiles, bundle_root)

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
        "package_mode": package_mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent_count": len(list(agents_dir.glob("*.md"))),
        "skill_count": len(list(skills_dir.glob("*.md"))),
        "memory_path": adapter["memory_path"],
        "continuation_prompt": adapter.get("continuation_prompt", "") if package_mode == PACKAGE_MODE_MAINTAINER else "",
        "bundle_root": str(bundle_root.relative_to(ROOT if bundle_root.is_relative_to(ROOT) else bundle_root.parent)),
        "runtime_entrypoint_count": len(runtime_entrypoints_for_mode(adapter, package_mode)),
        "graph_execution_status": adapter.get("graph_execution", {}).get("status", ""),
        "codex_native_agent_count": len(list((bundle_root / ".codex" / "agents").glob("*.md"))),
        "codex_native_command_count": len(list((bundle_root / ".codex" / "commands").glob("*.md"))),
        "codex_native_skill_count": len(list((bundle_root / ".codex" / "skills").glob("*.md"))),
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
        "- `.aikit/runtime-graph.json` — packaged workflow DAG metadata for runtime exploration",
        "- `.aikit/runtime-operating-protocol.md` — rules for CLI agents that call AIKit tools internally",
        "- `.aikit/runtime-continuation-contract.md` — continuation rules for resumed flows, lineage and next-step orchestration",
        "- `.aikit/runtime-tools.json` — machine-readable registry of internal AIKit tools",
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
    bundle_root = build_package(args.adapter, profiles_arg, packs, target_root, args.mode)
    print(f"Built adapter package: {bundle_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
