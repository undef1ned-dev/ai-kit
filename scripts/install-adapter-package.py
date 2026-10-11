#!/usr/bin/env python3
"""
Build and install an AIKit adapter bundle into a target workspace.

Usage:
    python scripts/install-adapter-package.py codex --profile vue-nuxt --workspace /tmp/my-codex-workspace
    python scripts/install-adapter-package.py glm --profile python-django --workspace /tmp/my-glm-workspace
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from memory_paths import ensure_memory_structure
from preset_utils import resolve_preset

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_MEMORY_INDEX = ROOT / "base" / "memory" / "INDEX.md"
COMMAND_SURFACE_FIXTURE = ROOT / "docs" / "fixtures" / "command-surface-inventory-fixtures.json"

INSTALL_MODE_CONSUMER = "consumer"
INSTALL_MODE_MAINTAINER = "maintainer"
ROOT_FILES_BLOCKED_IN_CONSUMER = {
    "AIKIT.md",
    "CLAUDE.md",
    "CONTINUE_AIKIT_MAINTAINER.md",
    "PRODUCT.md",
    "RUNTIME.md",
}
MAINTAINER_PROMPT_NAME = "CONTINUE_AIKIT_MAINTAINER.md"


def load_builder_module():
    path = ROOT / "scripts" / "build-adapter-package.py"
    spec = importlib.util.spec_from_file_location("aikit_build_adapter_package", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Unable to load builder module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_codex_command_surface_module():
    path = ROOT / "scripts" / "install-codex-command-surface.py"
    spec = importlib.util.spec_from_file_location("aikit_install_codex_command_surface", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Unable to load Codex command surface module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install AIKit adapter bundle into a workspace")
    parser.add_argument("adapter", help="adapter directory name under adapters/")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--profile", help="profile or profile1+profile2")
    selector.add_argument("--preset", help="preset name under presets/")
    parser.add_argument("--pack", action="append", default=[], help="optional pack name, can be repeated")
    parser.add_argument(
        "--workspace",
        required=True,
        help="target workspace where runtime files should be installed",
    )
    parser.add_argument(
        "--mode",
        choices=[INSTALL_MODE_CONSUMER, INSTALL_MODE_MAINTAINER],
        default=INSTALL_MODE_CONSUMER,
        help=(
            "install mode. consumer keeps AIKit under runtime/config directories; "
            "maintainer preserves AIKit development handoff files"
        ),
    )
    return parser.parse_args()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_frontmatter(text: str) -> dict[str, object]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL)
    if not match:
        return {}

    result: dict[str, object] = {}
    for line in match.group(1).splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        kv = re.match(r"^([\w][\w-]*):\s*(.*)", line)
        if not kv:
            continue
        key, raw_value = kv.group(1), kv.group(2).strip()
        if raw_value.startswith("[") and raw_value.endswith("]"):
            inner = raw_value[1:-1]
            result[key] = [item.strip().strip('"').strip("'") for item in inner.split(",") if item.strip()]
            continue
        if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in {'"', "'"}:
            result[key] = raw_value[1:-1]
            continue
        result[key] = raw_value
    return result


def strip_leading_frontmatter(text: str) -> str:
    return re.sub(r"^---\s*\n.*?\n---\s*\n?", "", text, count=1, flags=re.DOTALL)


def normalize_markdown_frontmatter_yaml(text: str) -> str:
    match = re.match(r"^---\s*\n(.*?)\n---(\s*\n.*|\s*)$", text, re.DOTALL)
    if not match:
        return text

    raw_frontmatter = match.group(1)
    remainder = match.group(2)
    normalized_lines: list[str] = []

    for line in raw_frontmatter.splitlines():
        stripped = line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            normalized_lines.append(stripped)
            continue

        kv = re.match(r"^([\w][\w-]*):\s*(.*)$", stripped)
        if not kv:
            normalized_lines.append(stripped)
            continue

        key, raw_value = kv.group(1), kv.group(2).strip()
        if not raw_value:
            normalized_lines.append(f"{key}: \"\"")
            continue

        if raw_value.startswith("[") and raw_value.endswith("]"):
            normalized_lines.append(f"{key}: {raw_value}")
            continue

        if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in {'"', "'"}:
            normalized_lines.append(f"{key}: {raw_value}")
            continue

        if raw_value in {"true", "false", "null"} or re.fullmatch(r"-?\d+(?:\.\d+)?", raw_value):
            normalized_lines.append(f"{key}: {raw_value}")
            continue

        normalized_lines.append(f"{key}: {json.dumps(raw_value, ensure_ascii=False)}")

    return "---\n" + "\n".join(normalized_lines) + "\n---" + remainder


def resolve_profiles_and_packs(profile_arg: str | None, preset_name: str | None, packs: list[str]) -> tuple[str, list[str]]:
    profiles_arg = profile_arg
    resolved_packs = list(packs)
    if preset_name:
        preset = resolve_preset(preset_name)
        profiles_arg = preset["profiles_arg"]
        resolved_packs = [*preset["packs"], *resolved_packs]
    if not profiles_arg:
        raise SystemExit("Either --profile or --preset must resolve to a profile selection")
    return profiles_arg, resolved_packs


def sync_bundle(bundle_root: Path, workspace: Path, skip_rel_paths: list[Path] | None = None) -> None:
    skip_paths = _unique_rel_paths(skip_rel_paths or [])

    def is_skipped(relative_path: Path) -> bool:
        normalized = Path(relative_path.as_posix().strip("/"))
        for skip_path in skip_paths:
            if normalized == skip_path or normalized.is_relative_to(skip_path):
                return True
        return False

    def copy_recursive(source: Path, destination: Path, relative_path: Path) -> None:
        if is_skipped(relative_path):
            return
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            for child in sorted(source.iterdir()):
                child_relative = relative_path / child.name if relative_path.parts else Path(child.name)
                copy_recursive(child, destination / child.name, child_relative)
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    for item in sorted(bundle_root.iterdir()):
        copy_recursive(item, workspace / item.name, Path(item.name))


def _unique_rel_paths(paths: list[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = path.as_posix().strip("/")
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(Path(key))
    return unique


def consumer_memory_paths(adapter: dict) -> list[Path]:
    adapter_memory_path = Path(str(adapter.get("memory_path", ".aikit/memory")).strip())
    return _unique_rel_paths(
        [
            Path(".aikit/memory"),
            adapter_memory_path,
        ]
    )


def ensure_consumer_memory_dirs(workspace: Path, rel_paths: list[Path]) -> None:
    for rel_path in rel_paths:
        target = workspace / rel_path
        if target.exists() and not target.is_dir():
            target.unlink()
        target.mkdir(parents=True, exist_ok=True)
        ensure_memory_structure(target, TEMPLATE_MEMORY_INDEX)


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def maintainer_command_file_names() -> set[str]:
    if not COMMAND_SURFACE_FIXTURE.exists():
        return set()
    data = read_json(COMMAND_SURFACE_FIXTURE)
    root_commands = data.get("root_commands", [])
    if not isinstance(root_commands, list):
        return set()
    names: set[str] = set()
    for item in root_commands:
        if not isinstance(item, dict) or item.get("scope") != "maintainer-local":
            continue
        path_text = str(item.get("path", "")).strip()
        if path_text:
            names.add(Path(path_text).name)
    return names


def strip_consumer_command_surfaces(workspace: Path) -> None:
    blocked_names = maintainer_command_file_names()
    if not blocked_names:
        return
    for commands_root in (workspace / ".codex" / "commands", workspace / ".claude" / "commands"):
        if not commands_root.exists():
            continue
        for file_name in blocked_names:
            remove_path(commands_root / file_name)


def write_consumer_runtime_guide(adapter: dict, workspace: Path) -> None:
    runtime = str(adapter.get("runtime", "")).strip()
    if not runtime:
        return

    runtime_root = workspace / f".{runtime}"
    if not runtime_root.exists():
        return

    guide_path = runtime_root / "AIKIT.md"
    if not guide_path.exists():
        return

    label = str(adapter.get("label", runtime)).strip()
    memory_path = str(adapter.get("memory_path", ".aikit/memory")).strip()
    guide = [
        f"# AIKit In {label}",
        "",
        "Этот workspace подключён к AIKit как consumer repo.",
        "",
        "## Что использовать",
        "",
        "- `.aikit/memory/` — общая командная память, которую можно ревьюить и хранить в git.",
        "- `.aikit/runtime/` — локальные runtime journals и RAG cache; не является source of truth.",
        f"- `{memory_path}` — canonical memory path для этого adapter bundle.",
        f"- `.{runtime}/agents/` — runtime-native mirror общих AIKit agents.",
        f"- `.{runtime}/skills/` — runtime-native mirror общих AIKit skills, если adapter его публикует.",
        f"- `.{runtime}/commands/` — runtime-native command surface, если adapter его публикует.",
        "- `.aikit/runtime-operating-protocol.md` — правила, по которым агент сам выбирает context, memory и validation tools.",
        "- `.aikit/runtime-tools.json` — machine-readable registry внутренних AIKit tools.",
        "",
        "## Правило consumer repo",
        "",
        "Не добавляй AIKit maintainer prompts или отдельные AIKit root markdown-файлы в репозиторий-потребитель.",
        "Если нужно изменить AIKit как продукт, делай это в source repo AIKit, а не через consumer workspace.",
    ]
    guide_path.write_text("\n".join(guide) + "\n", encoding="utf-8")


def strip_maintainer_entrypoints(path: Path) -> None:
    if not path.exists():
        return
    data = read_json(path)
    entrypoints = data.get("entrypoints")
    if not isinstance(entrypoints, list):
        return
    filtered = [
        entry
        for entry in entrypoints
        if not (
            isinstance(entry, dict)
            and (
                entry.get("name") == "continue-maintainer"
                or MAINTAINER_PROMPT_NAME in str(entry.get("path", ""))
            )
        )
    ]
    if len(filtered) != len(entrypoints):
        data["entrypoints"] = filtered
        write_json(path, data)


def strip_consumer_manifest_fields(path: Path) -> None:
    if not path.exists():
        return
    data = read_json(path)
    changed = False

    generated_artifacts = data.get("generated_artifacts")
    if isinstance(generated_artifacts, list):
        filtered_artifacts = [
            artifact
            for artifact in generated_artifacts
            if isinstance(artifact, str)
            and Path(artifact).name not in ROOT_FILES_BLOCKED_IN_CONSUMER
            and MAINTAINER_PROMPT_NAME not in artifact
        ]
        if filtered_artifacts != generated_artifacts:
            data["generated_artifacts"] = filtered_artifacts
            changed = True

    runtime_entrypoints = data.get("runtime_entrypoints")
    if isinstance(runtime_entrypoints, list):
        filtered_entrypoints = [
            entry
            for entry in runtime_entrypoints
            if not (
                isinstance(entry, dict)
                and (
                    entry.get("name") == "continue-maintainer"
                    or MAINTAINER_PROMPT_NAME in str(entry.get("path", ""))
                )
            )
        ]
        if filtered_entrypoints != runtime_entrypoints:
            data["runtime_entrypoints"] = filtered_entrypoints
            changed = True

    if data.get("continuation_prompt"):
        data["continuation_prompt"] = ""
        changed = True

    if changed:
        write_json(path, data)


def normalize_codex_skill_surface(workspace: Path) -> list[str]:
    skills_root = workspace / ".codex" / "skills"
    if not skills_root.exists():
        return []

    discovered: list[str] = []
    for flat_skill in sorted(skills_root.glob("*.md")):
        skill_name = flat_skill.stem
        skill_dir = skills_root / skill_name
        normalized = normalize_markdown_frontmatter_yaml(read_text(flat_skill))
        write_text(skill_dir / "SKILL.md", normalized)
        flat_skill.unlink()
        discovered.append(skill_name)

    for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            normalized = normalize_markdown_frontmatter_yaml(read_text(skill_file))
            write_text(skill_file, normalized)
            discovered.append(skill_dir.name)

    return sorted(set(discovered))


def render_codex_command_surface(workspace: Path) -> list[str]:
    commands_root = workspace / ".codex" / "commands"
    if not commands_root.exists():
        return []

    rendered: list[str] = []
    for command_path in sorted(commands_root.glob("*.md")):
        content = read_text(command_path)
        if re.search(r"(?m)^\s*#\s*/([a-z0-9]+(?:-[a-z0-9]+)*)\s*$", content):
            rendered.append(command_path.stem)
            continue

        metadata = parse_frontmatter(content)
        command_name = str(metadata.get("name") or command_path.stem).strip() or command_path.stem
        description = str(metadata.get("description") or "").strip()
        body = strip_leading_frontmatter(content).strip()

        lines = [f"# /{command_name}", ""]
        if description:
            lines.extend([description, ""])
        if body:
            lines.append(body)
            if not body.endswith("\n"):
                lines.append("")

        write_text(command_path, "\n".join(lines).rstrip() + "\n")
        rendered.append(command_name)

    return rendered


def render_codex_custom_agents(workspace: Path) -> list[dict[str, str]]:
    agents_root = workspace / ".codex" / "agents"
    if not agents_root.exists():
        return []

    rendered: list[dict[str, str]] = []
    for agent_file in sorted(agents_root.glob("*.md")):
        content = read_text(agent_file)
        metadata = parse_frontmatter(content)
        role_name = str(metadata.get("name") or agent_file.stem).strip()
        if not role_name:
            role_name = agent_file.stem
        description = str(metadata.get("description") or f"AIKit role {role_name}").strip()
        developer_instructions = strip_leading_frontmatter(content).strip()
        developer_instructions = developer_instructions.replace('"""', '\\"\\"\\"')
        toml_lines = [
            f"name = {json.dumps(role_name, ensure_ascii=False)}",
            f"description = {json.dumps(description, ensure_ascii=False)}",
            'developer_instructions = """',
            developer_instructions,
            '"""',
            "",
        ]
        toml_path = agents_root / f"{agent_file.stem}.toml"
        write_text(toml_path, "\n".join(toml_lines))
        rendered.append(
            {
                "name": role_name,
                "description": description,
                "config_path": f"agents/{toml_path.name}",
            }
        )

    stale_config_root = workspace / ".codex" / "agent-configs"
    if stale_config_root.exists():
        shutil.rmtree(stale_config_root)

    return rendered


def merge_codex_config_block(workspace: Path, skill_names: list[str], agent_roles: list[dict[str, str]]) -> None:
    config_path = workspace / ".codex" / "config.toml"
    begin_marker = "# BEGIN AIKIT GENERATED"
    end_marker = "# END AIKIT GENERATED"

    block_lines = [begin_marker]
    for skill_name in skill_names:
        block_lines.extend(
            [
                "[[skills.config]]",
                f"path = {json.dumps(f'skills/{skill_name}', ensure_ascii=False)}",
                "enabled = true",
                "",
            ]
        )
    for role in agent_roles:
        block_lines.extend(
            [
                f'[agents.{json.dumps(role["name"], ensure_ascii=False)}]',
                f'description = {json.dumps(role["description"], ensure_ascii=False)}',
                f'config_file = {json.dumps(role["config_path"], ensure_ascii=False)}',
                "",
            ]
        )
    block_lines.append(end_marker)
    rendered_block = "\n".join(block_lines).rstrip() + "\n"

    if config_path.exists():
        original = read_text(config_path)
        pattern = re.compile(
            rf"{re.escape(begin_marker)}.*?{re.escape(end_marker)}\n?",
            re.DOTALL,
        )
        if pattern.search(original):
            updated = pattern.sub(rendered_block, original)
        else:
            separator = "\n\n" if original.strip() else ""
            updated = original.rstrip() + separator + rendered_block
    else:
        updated = rendered_block

    write_text(config_path, updated)


def sync_codex_global_command_surface(workspace: Path) -> None:
    commands_root = workspace / ".codex" / "commands"
    if not commands_root.exists():
        return

    module = load_codex_command_surface_module()
    commands = module.load_commands(commands_root)
    prompts_target = Path(os.environ.get("AIKIT_CODEX_PROMPTS_TARGET", "~/.codex/prompts")).expanduser().resolve()
    skills_target = Path(os.environ.get("AIKIT_CODEX_SKILLS_TARGET", "~/.codex/skills")).expanduser().resolve()
    module.sync_prompts(commands, prompts_target)
    for stale_dir in sorted(skills_target.glob("aikit-command-*")):
        if stale_dir.is_dir():
            shutil.rmtree(stale_dir)


def prepare_codex_workspace_surface(workspace: Path) -> None:
    skill_names = normalize_codex_skill_surface(workspace)
    render_codex_command_surface(workspace)
    agent_roles = render_codex_custom_agents(workspace)
    merge_codex_config_block(workspace, skill_names, agent_roles)


def rewrite_text_file(path: Path, replacements: dict[str, str]) -> None:
    text = read_text(path)
    updated = text
    for old, new in replacements.items():
        updated = updated.replace(old, new)
    if updated != text:
        write_text(path, updated)


def apply_consumer_workspace_policy(adapter: dict, workspace: Path) -> None:
    blocked_root_files = set(ROOT_FILES_BLOCKED_IN_CONSUMER)
    if str(adapter.get("runtime", "")).strip() == "claude":
        blocked_root_files.discard("CLAUDE.md")

    for file_name in blocked_root_files:
        remove_path(workspace / file_name)

    runtime = str(adapter.get("runtime", "")).strip()
    if runtime:
        remove_path(workspace / f".{runtime}" / MAINTAINER_PROMPT_NAME)
        strip_maintainer_entrypoints(workspace / f".{runtime}" / "entrypoints.json")

    strip_maintainer_entrypoints(workspace / ".aikit" / "runtime-entrypoints.json")
    strip_consumer_manifest_fields(workspace / ".aikit" / "adapter.manifest.json")
    strip_consumer_manifest_fields(workspace / ".aikit" / "package.manifest.json")
    strip_consumer_command_surfaces(workspace)
    write_consumer_runtime_guide(adapter, workspace)


def rewrite_local_script_commands(workspace: Path, adapter: dict) -> None:
    runtime_tools_path = workspace / ".aikit" / "runtime-tools.json"
    if runtime_tools_path.exists():
        data = read_json(runtime_tools_path)
        for tool in data.get("tools", []):
            if not isinstance(tool, dict):
                continue
            command = tool.get("command")
            if (
                isinstance(command, list)
                and len(command) >= 2
                and command[0] in {"python", "python3"}
                and isinstance(command[1], str)
                and command[1].startswith("scripts/")
            ):
                command[1] = f".aikit-config/{command[1]}"
        write_json(runtime_tools_path, data)

    if str(adapter.get("runtime", "")).strip() != "codex":
        return

    codex_replacements = {
        ".claude/agents/": ".codex/agents/",
        ".claude/skills/": ".codex/skills/",
        ".claude/memory/": ".aikit/memory/",
        ".claude-config/": ".aikit-config/",
        "bash .claude-config/scripts/attach.sh <profile>": (
            "python3 .aikit-config/scripts/install-adapter-package.py "
            "codex --profile <profile> --workspace ."
        ),
    }
    for markdown_path in sorted((workspace / ".codex").rglob("*.md")):
        rewrite_text_file(markdown_path, codex_replacements)


def write_install_summary(adapter: dict, workspace: Path, bundle_root: Path, install_mode: str) -> None:
    summary = [
        f"# AIKit Install Summary — {adapter['label']}",
        "",
        f"- Runtime: `{adapter['runtime']}`",
        f"- Status: `{adapter['status']}`",
        f"- Install mode: `{install_mode}`",
        f"- Memory path: `{adapter['memory_path']}`",
        f"- Installed into: `{workspace}`",
        "",
        "## Next steps",
        "- Используй runtime-specific launcher внутри config root этого adapter.",
        "- Смотри `.aikit/runtime-entrypoints.json` как source of truth для runtime entrypoints этого workspace.",
        "- Смотри `.aikit/runtime-graph.json` как packaged workflow DAG surface для runtime exploration.",
        "- Смотри `.aikit/runtime-operating-protocol.md`, чтобы CLI-агент сам выбирал internal tools, memory и RAG обновления.",
        "- Смотри `.aikit/runtime-continuation-contract.md`, чтобы resumed flow, bundle handoff и lineage работали одинаково в этом runtime.",
        "- Смотри `.aikit/runtime-tools.json` как machine-readable registry внутренних AIKit tools.",
    ]
    if adapter.get("runtime") == "codex":
        summary.extend(
            [
                "- В Codex workspace используй custom agents в `.codex/agents/*.toml` и skills в `.codex/skills/*/SKILL.md` как основной runtime surface.",
                "- `.aikit/` остаётся canonical manifest и memory layer; `.codex/commands/` и `~/.codex/prompts` считаются compatibility-only alias surface.",
            ]
        )
    continuation = adapter.get("continuation_prompt", "")
    if continuation and install_mode == INSTALL_MODE_MAINTAINER:
        summary.append(f"- Для продолжения развития AIKit используй `{continuation}`.")
    if install_mode == INSTALL_MODE_CONSUMER:
        summary.append("- Root markdown-файлы AIKit maintainer mode не устанавливаются в consumer workspace.")
    summary.extend(
        [
            "",
            "## Source bundle",
            f"- Temporary build source: `{bundle_root}`",
        ]
    )
    (workspace / ".aikit" / "INSTALL.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


def install_package(
    adapter_name: str,
    profiles_arg: str,
    packs: list[str],
    workspace: Path,
    install_mode: str = INSTALL_MODE_CONSUMER,
) -> dict:
    workspace.mkdir(parents=True, exist_ok=True)

    builder = load_builder_module()
    adapter_manifest_path = ROOT / "adapters" / adapter_name / "adapter.manifest.json"
    if not adapter_manifest_path.exists():
        raise SystemExit(f"Adapter '{adapter_name}' not found at {adapter_manifest_path.relative_to(ROOT)}")
    adapter = read_json(adapter_manifest_path)

    with tempfile.TemporaryDirectory(prefix=f"aikit-install-{adapter_name}-") as temp_dir:
        temp_root = Path(temp_dir)
        memory_paths = consumer_memory_paths(adapter) if install_mode == INSTALL_MODE_CONSUMER else []
        bundle_root = builder.build_package(
            adapter_name,
            profiles_arg,
            packs,
            temp_root,
            package_mode=install_mode,
        )
        sync_bundle(bundle_root, workspace, skip_rel_paths=memory_paths if install_mode == INSTALL_MODE_CONSUMER else None)
        if install_mode == INSTALL_MODE_CONSUMER:
            apply_consumer_workspace_policy(adapter, workspace)
            ensure_consumer_memory_dirs(workspace, memory_paths)
        rewrite_local_script_commands(workspace, adapter)
        if str(adapter.get("runtime", "")).strip() == "codex":
            prepare_codex_workspace_surface(workspace)
            sync_codex_global_command_surface(workspace)
        write_install_summary(adapter, workspace, bundle_root, install_mode)

    return adapter


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    profiles_arg, packs = resolve_profiles_and_packs(args.profile, args.preset, list(args.pack))
    install_package(args.adapter, profiles_arg, packs, workspace, args.mode)

    print(f"Installed adapter package '{args.adapter}' into {workspace}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
