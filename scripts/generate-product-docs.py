#!/usr/bin/env python3
"""
Generate product-facing release and install docs from AIKit source-of-truth files.

Outputs:
- docs/public/release-center.md
- docs/public/install-matrix.md
- docs/public/get-started.md
- docs/public/product-story.md
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from docs_paths import repo_relative_path
from release_utils import read_version, unreleased_has_entries


ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
PUBLIC_DOCS_DIR = DOCS_DIR / "public"
VERSION_FILE = ROOT / "VERSION"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"
RELEASE_CENTER_DOC = PUBLIC_DOCS_DIR / "release-center.md"
INSTALL_MATRIX_DOC = PUBLIC_DOCS_DIR / "install-matrix.md"
GET_STARTED_DOC = PUBLIC_DOCS_DIR / "get-started.md"
PRODUCT_STORY_DOC = PUBLIC_DOCS_DIR / "product-story.md"
CONTINUITY_FIXTURE = DOCS_DIR / "fixtures" / "continuity-brief-fixtures.json"
PUBLIC_OPERATING_CLASSES = {"product-project"}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def continuity_surface() -> dict:
    data = read_json(CONTINUITY_FIXTURE)
    surface = data.get("aikit_repo_surface", {})
    return surface if isinstance(surface, dict) else {}


def parse_changelog_sections(text: str) -> tuple[str, list[dict[str, str]]]:
    unreleased_lines: list[str] = []
    releases: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line == "## [Unreleased]":
            if current:
                current["body"] = "\n".join(current_lines).strip()
                releases.append(current)
            current = {"version": "Unreleased", "date": "", "body": ""}
            current_lines = []
            continue

        match = re.match(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\] - (\d{4}-\d{2}-\d{2})$", line)
        if match:
            if current:
                current["body"] = "\n".join(current_lines).strip()
                if current["version"] == "Unreleased":
                    unreleased_lines = current["body"].splitlines()
                else:
                    releases.append(current)
            current = {"version": match.group(1), "date": match.group(2), "body": ""}
            current_lines = []
            continue

        if current is not None:
            current_lines.append(raw_line)

    if current:
        current["body"] = "\n".join(current_lines).strip()
        if current["version"] == "Unreleased":
            unreleased_lines = current["body"].splitlines()
        else:
            releases.append(current)

    unreleased = "\n".join(line for line in unreleased_lines if line.strip()).strip()
    return unreleased, releases


def sanitize_public_release_notes(text: str) -> str:
    replacements = {
        "`aikit-maintainer`": "packaged maintainer flow",
    }
    sanitized = text
    for source, target in replacements.items():
        sanitized = sanitized.replace(source, target)
    return sanitized


def collect_adapters() -> list[dict]:
    adapters = []
    for path in sorted((ROOT / "adapters").glob("*/adapter.manifest.json")):
        data = read_json(path)
        graph = data.get("graph_execution", {})
        adapters.append(
            {
                "name": path.parent.name,
                "label": data.get("label", path.parent.name),
                "runtime": data.get("runtime", ""),
                "status": data.get("status", ""),
                "install_type": data.get("install_type", ""),
                "update_script": data.get("update_script", ""),
                "memory_path": data.get("memory_path", ""),
                "entrypoint_style": data.get("entrypoint_style", ""),
                "continuation": bool(data.get("continuation_prompt")),
                "runtime_entrypoints": len(data.get("runtime_entrypoints", [])),
                "graph_status": graph.get("status", "—") if isinstance(graph, dict) else "—",
            }
        )
    return adapters


def collect_presets() -> list[dict]:
    presets = []
    for path in sorted((ROOT / "presets").glob("*.json")):
        data = read_json(path)
        presets.append(
            {
                "name": data.get("name", path.stem),
                "label": data.get("label", path.stem),
                "description": data.get("description", ""),
                "profiles": data.get("profiles", []),
                "packs": data.get("packs", []),
                "recommended_adapter": data.get("recommended_adapter", ""),
                "lifecycle": data.get("lifecycle", {}),
            }
        )
    return presets


def public_presets(presets: list[dict]) -> list[dict]:
    return [preset for preset in presets if preset.get("lifecycle", {}).get("status") != "deprecated"]


def deprecated_presets(presets: list[dict]) -> list[dict]:
    return [preset for preset in presets if preset.get("lifecycle", {}).get("status") == "deprecated"]


def collect_profiles() -> list[dict]:
    profiles = []
    for path in sorted((ROOT / "profiles").glob("*/profile.manifest.json")):
        data = read_json(path)
        taxonomy = data.get("taxonomy", {})
        if not isinstance(taxonomy, dict):
            taxonomy = {}
        profiles.append(
            {
                "name": data.get("profile", path.parent.name),
                "label": data.get("label", path.parent.name),
                "domain": data.get("domain", ""),
                "visibility": data.get("visibility", {}),
                "operating_class": taxonomy.get("operating_class", "product-project"),
                "direction": taxonomy.get("direction", ""),
                "ecosystem": taxonomy.get("ecosystem", ""),
                "framework": taxonomy.get("framework", ""),
                "domain_family": taxonomy.get("domain_family", data.get("domain", "")),
                "stack_profile": taxonomy.get("stack_profile", data.get("profile", path.parent.name)),
                "core_roles": taxonomy.get("core_role_set", []),
                "recommended_packs": data.get("recommended_packs", []),
                "recommended_skills": data.get("recommended_skills", []),
                "path_signals": data.get("path_signals", []),
            }
        )
    return profiles


def public_profiles(profiles: list[dict]) -> list[dict]:
    return [
        profile
        for profile in profiles
        if profile["operating_class"] in PUBLIC_OPERATING_CLASSES
        and profile.get("visibility", {}).get("scope") != "deprecated-demo-internal"
        and profile.get("visibility", {}).get("public_adoption_default") is not False
    ]


def active_runtime_adapters(adapters: list[dict]) -> list[dict]:
    return [adapter for adapter in adapters if adapter["status"] == "active" and adapter["runtime"] != "claude"]


def generate_release_center() -> str:
    current_version = read_version(VERSION_FILE)
    changelog = CHANGELOG_FILE.read_text(encoding="utf-8")
    unreleased, releases = parse_changelog_sections(changelog)
    unreleased = sanitize_public_release_notes(unreleased)
    releases = [
        {
            **release,
            "body": sanitize_public_release_notes(str(release.get("body", ""))),
        }
        for release in releases
    ]
    latest = releases[0] if releases else {"version": current_version, "date": "—", "body": ""}
    has_unreleased_entries = unreleased_has_entries(changelog)
    compatibility_verdict = "compatible with current install/update flows"
    breaking_verdict = "none declared in Unreleased"
    if "Support analytics and release candidate evidence triage" in unreleased:
        update_verdict = "Local support analytics and release candidate evidence triage is staged for review. No release is published."
        candidate_review_status = "`candidate-review-only`"
    else:
        update_verdict = (
            "Review `Unreleased`, then use the runtime update flow after the next release is prepared."
            if has_unreleased_entries
            else "No product-facing update is pending in `Unreleased`."
        )
        candidate_review_status = ""
    version_link = repo_relative_path(VERSION_FILE, RELEASE_CENTER_DOC)
    changelog_link = repo_relative_path(CHANGELOG_FILE, RELEASE_CENTER_DOC)

    lines = [
        "# Release Center",
        "",
        "Этот документ генерируется из `VERSION` и `CHANGELOG.md`.",
        "Он показывает release state AIKit как продуктовой платформы, а не только как внутреннего git-репозитория.",
        "",
        f"- Current version: `{current_version}`",
        f"- Latest released version: `{latest['version']}`",
        f"- Latest release date: `{latest['date']}`",
        "",
        "## Should I Update?",
        "",
        f"- Compatibility verdict: `{compatibility_verdict}`",
        f"- Breaking changes: `{breaking_verdict}`",
        f"- Update verdict: {update_verdict}",
        *([f"- Candidate review status: {candidate_review_status}"] if candidate_review_status else []),
        "- Claude workspace update: `bash .aikit-config/scripts/update.sh`",
        "- Runtime workspace update command: `/aikit-runtime-workspace <adapter> --preset <preset> --workspace <path> --operation update`",
        "- Runtime workspace command wraps install/update/bootstrap implementation details.",
        "- Release details: see `CHANGELOG.md` and the `Unreleased` section below.",
        "",
        "## Current State",
        "",
        f"- Source of truth version file: [`VERSION`]({version_link})",
        f"- Changelog source: [`CHANGELOG.md`]({changelog_link})",
        "- Release validation: `/aikit-doctor --check validate-release`",
        "- Release prep flow: `/aikit-command-center release --version <semver> --date YYYY-MM-DD`",
        "",
        "## Unreleased",
        "",
    ]

    if unreleased:
        lines.append(unreleased)
    else:
        lines.append("- Пока пусто.")

    lines.extend(
        [
            "",
            "## Latest Release Snapshot",
            "",
            f"### `{latest['version']}` — {latest['date']}",
            "",
        ]
    )
    if latest["body"]:
        lines.append(latest["body"])
    else:
        lines.append("- Release notes пока отсутствуют.")

    lines.extend(
        [
            "",
            "## Release Workflow",
            "",
            "1. Обновить `CHANGELOG.md` в секции `Unreleased`.",
            "2. Подготовить следующий релиз через `/aikit-command-center release --version <semver> --date YYYY-MM-DD`.",
            "3. Прогнать `/aikit-doctor --check validate-release` и `/aikit-doctor --check validate-config`.",
            "4. Если менялись installer/build/docs scripts, прогнать `py_compile`, `bash -n` и product generators.",
            "5. Не готовить релиз, пока `Unreleased` содержит только placeholder `- Пока пусто.`.",
            "",
            "## Product Signals",
            "",
            "- Release version встраивается в adapter packages как `repo_version`.",
            "- Install/update flows используют root `VERSION` как source of truth.",
            "- Generated docs позволяют смотреть release/install состояние без чтения кода скриптов.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def generate_install_matrix() -> str:
    adapters = collect_adapters()
    all_presets = collect_presets()
    presets = public_presets(all_presets)
    archived_presets = deprecated_presets(all_presets)
    lines = [
        "# Install Matrix",
        "",
        "Этот документ генерируется из adapter manifests и preset manifests.",
        "Он показывает, как AIKit устанавливается в разные runtime и какие bundle shortcuts уже доступны команде.",
        "",
        "## Fast Install Shape",
        "",
        "AIKit keeps the public install surface short and command-first:",
        "",
        "1. install a preset or runtime workspace;",
        "2. run `/aikit-bootstrap-project`;",
        "3. verify install readiness with `/aikit-doctor --scope install`;",
        "4. choose one first task command from `docs/public/start-here.md`.",
        "",
        "Backing runners remain implementation details. User-facing docs should show the command wrapper first and only explain the backing runner when debugging an install issue.",
        "",
        "## Runtime Install Surface",
        "",
        "| Adapter | Runtime | Status | Install flow | Update flow | Entrypoint style | Continuation | Runtime entrypoints | Graph execution | Memory path |",
        "|---------|---------|--------|--------------|-------------|------------------|--------------|---------------------|-----------------|-------------|",
    ]
    for adapter in adapters:
        update_flow = "`yes`" if adapter["update_script"] else "`no`"
        lines.append(
            f"| `{adapter['name']}` | `{adapter['runtime']}` | `{adapter['status']}` | `{adapter['install_type'] or '—'}` | {update_flow} | `{adapter['entrypoint_style']}` | `{'yes' if adapter['continuation'] else 'no'}` | `{adapter['runtime_entrypoints']}` | `{adapter['graph_status']}` | `{adapter['memory_path']}` |"
        )

    lines.extend(
        [
            "",
            "## Team Presets",
            "",
            "| Preset | Profiles | Packs | Recommended adapter |",
            "|--------|----------|-------|---------------------|",
        ]
    )
    for preset in presets:
        profiles = ", ".join(f"`{item}`" for item in preset["profiles"]) or "—"
        packs = ", ".join(f"`{item}`" for item in preset["packs"]) or "—"
        adapter = f"`{preset['recommended_adapter']}`" if preset["recommended_adapter"] else "—"
        lines.append(f"| `{preset['name']}` | {profiles} | {packs} | {adapter} |")

    if archived_presets:
        lines.extend(
            [
                "",
                "## Deprecated Preset Archive",
                "",
                "These presets remain source-resolvable for compatibility, but they are not public/default install choices.",
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
            "## Recommended First-Run Path",
            "",
            "1. Install preset: `bash .aikit-config/scripts/attach.sh --preset frontend-team`",
            "2. Bootstrap: `/aikit-bootstrap-project`",
            "3. Check install status: `/aikit-doctor --scope install`",
            "4. Choose one first task command from `docs/public/start-here.md`.",
            "",
            "Advanced/runtime alternatives stay below this primary path.",
            "",
            "## Distribution Plan Commands",
            "",
            "- Inspect all commands for a preset: `/aikit-install-update inspect --preset frontend-team`",
            "- Inspect commands for one runtime: `/aikit-install-update inspect --preset frontend-team --adapter codex`",
            "- Machine-readable distribution plan: `/aikit-install-update inspect --preset frontend-team --adapter codex --json`",
            "",
            "## What Happened After Install",
            "",
            "| Path | Runtime | Purpose |",
            "|------|---------|---------|",
            "| `CLAUDE.md` | `claude` | Combined project instruction surface for Claude Code. |",
            "| `.claude/commands/` | `claude` | Slash-command files generated from selected profiles and packs. |",
            "| `.claude/agents/` | `claude` | Runtime-visible specialist agents. |",
            "| `.claude/.config-version` | `claude` | Installed AIKit version marker for update checks. |",
            "| `.aikit/memory/` | all runtimes | Canonical memory root shared across supported adapters. |",
            "| `.claude/memory/` | `claude` | Claude mirror of canonical memory. |",
            "| `.aikit/runtime-entrypoints.json` | non-Claude | Machine-readable launcher surface for runtime workspaces. |",
            "| `.aikit/runtime-tools.json` | non-Claude | Internal tool registry exposed to the installed runtime. |",
            "| `.aikit/runtime-continuation-contract.md` | non-Claude | Continuation rules for resumed runtime flows. |",
            "| `AGENTS.md` | `codex`, `opencode` | Project rules; the AIKit block is managed by the installer, user content outside it is kept. |",
            "| `.agents/skills/` | `codex`, `opencode` | AIKit skills in the Agent Skills format (`<name>/SKILL.md`). |",
            "| `.codex/agents/*.toml` | `codex` | AIKit agents as Codex custom agents. |",
            "| `.opencode/agents/` | `opencode` | AIKit agents as OpenCode subagents. |",
            "",
            "Users run slash commands. Python scripts are diagnostics, CI and internal runner implementation details.",
            "",
            "## Post-Install Verification",
            "",
            "After install, verify in this order:",
            "",
            "1. `/aikit-bootstrap-project`",
            "2. read `BOOTSTRAP_REPORT` and confirm selected/ignored refs",
            "3. `/aikit-doctor --scope install`",
            "4. choose exactly one next task command from `docs/public/start-here.md`",
            "",
            "## Support Quality Gate",
            "",
            "`ADAPTER_SUPPORT_SCORECARD` is the local support quality gate for Claude Code, Codex and OpenCode. It ranks install/update, runtime workspace recovery, command recovery and public docs parity evidence without adding new runtime capability claims.",
            "",
            "When support evidence points to adapter drift, use the existing repair commands and rerun Doctor before starting task work.",
            "",
            "## Troubleshooting",
            "",
            "Use this recovery path before opening reference catalogs:",
            "",
            "```text",
            "/aikit-doctor --scope install",
            "/aikit-install-update inspect --preset frontend-team --adapter codex",
            "/aikit-runtime-workspace codex --preset frontend-team --workspace /tmp/aikit-codex --operation update",
            "/aikit-doctor --scope install",
            "```",
            "",
            "The first command checks readiness, the update command is the recommended repair command for stale Codex runtime workspaces and the final Doctor run is the rerun command.",
            "",
            "## Already Installed? Update Path",
            "",
            "| Runtime | Update command | Verify after update |",
            "|---------|----------------|---------------------|",
            "| `claude` | `bash .aikit-config/scripts/update.sh` | `/aikit-doctor --scope install` |",
            "| `codex` | `/aikit-runtime-workspace codex --preset frontend-team --workspace /tmp/aikit-codex --operation update` | `/aikit-doctor --check validate-adapter-fixtures` |",
            "| `opencode` | `/aikit-runtime-workspace opencode --preset frontend-team --workspace /tmp/aikit-opencode --operation update` | `/aikit-doctor --check validate-adapter-fixtures` |",
            "",
            "## Reading the Matrix",
            "",
            "- `status` показывает maturity адаптера как runtime surface.",
            "- `install flow` показывает, есть ли у runtime собственный install contract, а не только package builder.",
            "- `update flow` показывает, может ли runtime безопасно пересинхронизировать уже установленный workspace.",
            "- `runtime entrypoints` показывает, насколько адаптер умеет публиковать actionable launcher surface.",
            "- `graph execution` показывает maturity packaged DAG metadata для orchestration recipes.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def generate_get_started() -> str:
    adapters = collect_adapters()
    presets = public_presets(collect_presets())
    active_adapters = active_runtime_adapters(adapters)
    active_adapter_names = ", ".join(f"`{adapter['name']}`" for adapter in active_adapters) or "—"

    lines = [
        "# Get Started",
        "",
        "Этот документ генерируется из presets и adapter manifests.",
        "Его задача — дать самый короткий путь в AIKit без необходимости сначала читать весь каталог документации.",
        "",
        "## Fast Install",
        "",
        "Claude production path from the target project:",
        "",
        "```bash",
        "git submodule add git@github.com:undef1ned-dev/ai-kit.git .aikit-config",
        "git submodule update --init",
        "bash .aikit-config/scripts/attach.sh --preset frontend-team",
        "```",
        "",
        "Runtime workspace path:",
        "",
        "```text",
        "/aikit-runtime-workspace codex --preset frontend-team --workspace /tmp/aikit-codex",
        "```",
        "",
        "Use `/aikit-install-update inspect --preset frontend-team --adapter codex --json` when you need the install/update plan before writing a workspace.",
        "",
        "## One Developer Journey",
        "",
        "1. Install preset через attach или runtime workspace flow. Для non-Claude install flow используй `/aikit-runtime-workspace`.",
        "2. Запусти `/aikit-bootstrap-project`.",
        "3. Прочитай `BOOTSTRAP_REPORT` и затем проверь `/aikit-doctor --scope install`.",
        "4. Выбери один рабочий slash command из `docs/public/start-here.md`.",
        "5. Используй `docs/index.html` как generated overview этого пути, а `docs/public/agents-skills-reference.md` открывай только после того, как задача уже понятна.",
        "",
        "## Choose Your Path",
        "",
        "### 1. Production path for Claude",
        "",
        "- Если тебе нужен самый стабильный и production-ready сценарий, начни с `Claude`.",
        "- Выбери подходящий preset и подключи AIKit через `attach.sh`.",
        "",
        "### 2. Runtime evaluation path",
        "",
        f"- Если хочешь попробовать non-Claude runtime, сейчас production-supported adapters: {active_adapter_names}.",
        "- Для них используй `/aikit-runtime-workspace <runtime> --preset <preset> --workspace <path>`; Python scripts остаются internal runner layer.",
        "",
        "### 3. Compare runtimes before adopting",
        "",
        "- Смотри `docs/public/install-matrix.md` для install surface.",
        "- Смотри `docs/public/runtime-maturity-review.md` для maturity verdict.",
        "- Смотри `docs/public/compatibility-matrix.md` для общей платформенной картины.",
        "",
        "### 4. Start from the first command, not from internal systems",
        "",
        "- После attach или install первым visible command должен быть `/aikit-bootstrap-project`.",
        "- После `BOOTSTRAP_REPORT` выбери один рабочий slash command из `docs/public/start-here.md`.",
        "- Если хочешь понять, какой путь подходит твоей команде, начни с `docs/public/product-story.md`.",
        "- Там собраны готовые сценарии adoption: production rollout, multi-runtime evaluation, team presets and platform curation.",
        "",
        "## What The Install Flow Does",
        "",
        "- resolves the selected preset, profiles and packs;",
        "- writes the runtime-facing agents, skills and command files;",
        "- initializes canonical `.aikit/memory/` and runtime mirrors;",
        "- records config version metadata for update checks;",
        "- for non-Claude workspaces, publishes runtime entrypoints, runtime tools and continuation contracts;",
        "- runs bootstrap when the lifecycle command is not explicitly told to skip it.",
        "",
        "The install surface should feel short; the generated artifacts stay explicit so operators can inspect what changed.",
        "",
        "## Preset Quick Starts",
        "",
        "| Preset | Best first step | Claude production | Codex workspace | OpenCode workspace |",
        "|--------|-----------------|-------------------|-----------------|--------------------|",
    ]

    for preset in presets:
        preset_name = preset["name"]
        description = preset["description"]
        claude_cmd = f"`bash .aikit-config/scripts/attach.sh --preset {preset_name}`"
        codex_cmd = f"`/aikit-runtime-workspace codex --preset {preset_name} --workspace /tmp/aikit-codex`"
        opencode_cmd = f"`/aikit-runtime-workspace opencode --preset {preset_name} --workspace /tmp/aikit-opencode`"
        lines.append(
            f"| `{preset_name}` | {description} | {claude_cmd} | {codex_cmd} | {opencode_cmd} |"
        )

    lines.extend(
        [
            "",
            "## Runtime Adoption Guide",
            "",
            "| Runtime | When to choose it | First command |",
            "|---------|-------------------|---------------|",
            "| `claude` | Нужен основной production flow AIKit c slash-командами и attach/update contract. | `bash .aikit-config/scripts/attach.sh --preset frontend-team` |",
        ]
    )
    for adapter in active_adapters:
        runtime = adapter["runtime"]
        workspace = f"/tmp/aikit-{runtime}"
        lines.append(
            f"| `{runtime}` | Нужен production-supported non-Claude runtime с install/update flow и continuation handoff. | `/aikit-runtime-workspace {runtime} --preset frontend-team --workspace {workspace}` |"
        )
    for adapter in adapters:
        if adapter["status"] != "active" and adapter["runtime"] != "claude":
            runtime = adapter["runtime"]
            workspace = f"/tmp/aikit-{runtime}"
            lines.append(
                f"| `{runtime}` | Нужен exploratory runtime target для оценки adapter surface до production adoption. | `/aikit-runtime-workspace {runtime} --preset frontend-team --workspace {workspace}` |"
            )

    lines.extend(
        [
            "",
            "## Slash Commands You Should See",
            "",
            "- `/aikit-bootstrap-project` — first-run discovery command.",
            "- `/implement-feature` — default delivery command for normal work.",
            "- `/design-implement` and `/design-review` — design-scoped overlays.",
            "- `/security-check` — focused follow-up command for security audit work.",
            "",
            "## Post-Install Verification",
            "",
            "After install, run checks in this order:",
            "",
            "1. `/aikit-bootstrap-project` — generate `BOOTSTRAP_REPORT` before implementation.",
            "2. Review selected refs, ignored refs and memory candidates.",
            "3. `/aikit-doctor --scope install` — confirm install preset, bootstrap, doctor and first-task readiness.",
            "4. Start one task command from `docs/public/start-here.md`.",
            "",
            "Stop if bootstrap selects unsafe refs, asks for durable memory writes directly or suggests a next command that does not match the actual task.",
            "",
            "## Progressive Context Model",
            "",
            "AIKit should show lightweight evidence first and let the workflow fetch details only when useful:",
            "",
            "- `BOOTSTRAP_REPORT` shows selected refs, ignored refs and evidence-card counts;",
            "- context packs show source refs, trust labels and reasons before deeper reading;",
            "- memory candidates stay review-required until a workflow promotes them;",
            "- agents should prefer command and report surfaces before opening large reference catalogs.",
            "",
            "## Runtime Lifecycle Command",
            "",
            "- `/aikit-runtime-workspace` — user-facing runtime workspace install/update/bootstrap path.",
            "- Internal scripts such as `scripts/run-runtime-workspace.py`, `scripts/install-adapter-package.py` and `scripts/update-adapter-package.py` remain implementation details for the command.",
            "",
            "Profile-specific overlays such as `/setup-admin` stay inside profile references after the task is known; they are not part of the global first-screen command set.",
            "",
            "## What To Read Next",
            "",
            "- `docs/public/start-here.md` — task-first human entry surface: bootstrap, feature work, design and security work.",
            "- `docs/public/release-center.md` — понять текущую версию, update verdict и release workflow.",
            "- `docs/public/product-story.md` — use-case map: кто и зачем использует AIKit, с какими next steps.",
            "- `docs/index.html` — generated docs-home overview for the same start-working flow.",
            "- `docs/catalog.html` — browse/reference surface после того, как первый task route уже выбран.",
            "- `docs/public/install-matrix.md` — понять install/update surface, distribution commands и update path для runtime adapters.",
            "- `docs/public/runtime-maturity-review.md` — понять, какие runtimes уже production-supported.",
        "- `docs/public/marketplace.md` и `docs/public/publishing-workflow.md` — если хочешь сравнить presets, packs и distribution surfaces без углубления во внутренние maintainer workflows.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def generate_product_story() -> str:
    profiles = public_profiles(collect_profiles())
    presets = public_presets(collect_presets())
    adapters = collect_adapters()
    active_adapters = active_runtime_adapters(adapters)

    preset_lines = []
    for preset in presets:
        profiles_value = ", ".join(f"`{item}`" for item in preset["profiles"]) or "—"
        packs_value = ", ".join(f"`{item}`" for item in preset["packs"]) or "—"
        adapter_value = f"`{preset['recommended_adapter']}`" if preset["recommended_adapter"] else "—"
        preset_lines.append(
            f"| `{preset['name']}` | {preset['description']} | {profiles_value} | {packs_value} | {adapter_value} |"
        )

    profile_lines = []
    for profile in profiles:
        skills_value = ", ".join(f"`{item}`" for item in profile["recommended_skills"]) or "—"
        packs_value = ", ".join(f"`{item}`" for item in profile["recommended_packs"]) or "—"
        path_signals = ", ".join(f"`{item}`" for item in profile["path_signals"][:4]) or "—"
        core_roles = ", ".join(f"`{item}`" for item in profile["core_roles"]) or "—"
        profile_lines.append(
            f"| `{profile['name']}` | `{profile['operating_class']}` | `{profile['direction'] or '—'}` | `{profile['ecosystem'] or '—'}` | `{profile['framework'] or '—'}` | `{profile['domain_family']}` | `{profile['domain']}` | `{profile['stack_profile']}` | {core_roles} | {skills_value} | {packs_value} | {path_signals} |"
        )

    active_runtimes = ", ".join(f"`{adapter['runtime']}`" for adapter in active_adapters) or "—"

    lines = [
        "# Product Story",
        "",
        "Этот документ генерируется из profile, preset и adapter manifests.",
        "Его задача — связать release/install/catalog/marketplace surfaces в одну понятную продуктовую историю: кто использует AIKit, зачем и какой следующий шаг делать.",
        "",
        "## What AIKit Is",
        "",
        "- AIKit — это operating layer для инженерных AI workflow, а не просто набор markdown-промптов.",
        "- Система связывает profiles, skills, runtime adapters, presets и memory model в единый reproducible setup.",
        "- Один и тот же core может жить в `Claude`, `Codex`, `OpenCode` и будущих runtime без форков контента.",
        "",
        "## Use Cases",
        "",
        "### 0. Task-first entry after bootstrap",
        "",
        "- Если пользователь начинает с существующего репозитория, первым экраном должен быть `docs/public/start-here.md`.",
        "- Этот путь начинается с `/aikit-bootstrap-project`, объясняет `BOOTSTRAP_REPORT` и предлагает один следующий command по outcome.",
        "- Начать: `docs/public/start-here.md` → `docs/public/bootstrap-report-guide.md` → `docs/public/prompt-cookbook.md`.",
        "",
        "### 1. Production rollout inside an existing project",
        "",
        "- Выбери preset под команду и подключи AIKit через `attach.sh`.",
        "- Это путь, если тебе нужна минимальная цена входа и готовый production flow с profile routing, skills и memory.",
        "- Начать: `docs/public/get-started.md` → `docs/public/install-matrix.md` → `docs/catalog.html`.",
        "",
        "### 2. Multi-runtime adoption without rewriting workflows",
        "",
        f"- Если команда хочет использовать несколько runtime, AIKit уже поддерживает active non-Claude adapters: {active_runtimes}.",
        "- Это путь, если тебе важно сохранить core workflows и при этом запускать их в разных инструментах.",
        "- Начать: `docs/public/runtime-maturity-review.md` → `docs/public/install-matrix.md` → `docs/public/compatibility-matrix.md`.",
        "",
        "### 3. Team bundle onboarding",
        "",
        "- Presets превращают profile + packs в дешёвый onboarding path для конкретной команды.",
        "- Это путь, если ты хочешь быстро развернуть frontend, backend или fullstack сценарий без ручной сборки конфигурации.",
        "- Начать: `docs/public/get-started.md` → `docs/public/profiles-summary.md` → `docs/catalog.html`.",
        "",
        "### 4. Compare bundles and distribution surfaces",
        "",
        "- Marketplace and publishing surfaces explain which packs, presets and adapters already exist for project adoption.",
        "- Это путь, если тебе нужно сравнить bundle options и понять distribution surface, а не вести внутренний maintainer publishing flow вручную.",
        "- Начать: `docs/public/marketplace.md` → `docs/public/publishing-workflow.md` → `docs/public/install-matrix.md`.",
        "",
        "### 5. Continuity value before broader rollout",
        "",
        "- AIKit treats continuity value as something to falsify with a memory-on vs memory-off counterfactual before it is marketed as a durable product claim.",
        "- The evaluation path must stay local, deterministic and measurable: source refs, drift detection, outcome delta and review paths come before adoption claims.",
        "- Начать: `docs/internal/continuity-cold-resume-pilot.md` → `docs/internal/memory-off-counterfactual-pilot.md` → `docs/internal/shared-memory-contamination-metrics.md`.",
        "",
        "## Which Path To Choose",
        "",
        "| If you need... | Start here | Then go to |",
        "|----------------|------------|------------|",
        "| Понять, какую команду запускать после bootstrap | `docs/public/start-here.md` | `docs/public/bootstrap-report-guide.md` |",
        "| Быстро внедрить AIKit в рабочий проект | `docs/public/get-started.md` | `docs/public/install-matrix.md` |",
        "| Сравнить runtime и выбрать не только Claude | `docs/public/runtime-maturity-review.md` | `docs/public/compatibility-matrix.md` |",
        "| Понять профили, агенты и skills под задачу | `docs/catalog.html` | `docs/public/profiles-summary.md` |",
        "| Сравнить presets, packs и adapters как distribution surface | `docs/public/marketplace.md` | `docs/public/publishing-workflow.md` |",
        "| Проверить continuity value перед rollout | `docs/internal/continuity-cold-resume-pilot.md` | `docs/internal/memory-off-counterfactual-pilot.md` |",
        "",
        "## Team Presets As Product Entry",
        "",
        "| Preset | Best fit | Profiles | Packs | Recommended adapter |",
        "|--------|----------|----------|-------|---------------------|",
        *preset_lines,
        "",
        "## Domain Profiles",
        "",
        "| Profile | Operating class | Direction | Ecosystem | Framework | Domain family | Legacy domain | Stack profile | Core roles | Recommended skills | Recommended packs | Typical path signals |",
        "|---------|-----------------|-----------|-----------|-----------|---------------|---------------|---------------|------------|--------------------|-------------------|----------------------|",
        *profile_lines,
        "",
        "## Product Surface Map",
        "",
        "- `docs/index.html` — docs portal и рекомендуемые journeys.",
        "- `docs/public/start-here.md` — task-first entry surface поверх bootstrap report.",
        "- `docs/public/get-started.md` — самый короткий путь входа.",
        "- `docs/catalog.html` — browse-слой по агентам, skills и profile coverage.",
        "- `docs/public/release-center.md` — release state платформы.",
        "- `docs/public/install-matrix.md` — install/update surface по runtime.",
        "- `docs/public/compatibility-matrix.md` — платформенная картина по adapters, profiles и presets.",
        "- `docs/public/marketplace.md` и `docs/public/publishing-workflow.md` — distribution surface для presets, packs и adapters.",
        "",
        "## Recommended Reading Order",
        "",
        "1. `docs/public/product-story.md`",
        "2. `docs/public/start-here.md`",
        "3. `docs/public/get-started.md`",
        "4. `docs/index.html`",
        "5. `docs/catalog.html`",
        "6. Далее — специализированный surface под твой путь: install, runtime maturity, distribution surface или release.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    RELEASE_CENTER_DOC.write_text(generate_release_center(), encoding="utf-8")
    INSTALL_MATRIX_DOC.write_text(generate_install_matrix(), encoding="utf-8")
    GET_STARTED_DOC.write_text(generate_get_started(), encoding="utf-8")
    PRODUCT_STORY_DOC.write_text(generate_product_story(), encoding="utf-8")
    print(f"Updated {RELEASE_CENTER_DOC}")
    print(f"Updated {INSTALL_MATRIX_DOC}")
    print(f"Updated {GET_STARTED_DOC}")
    print(f"Updated {PRODUCT_STORY_DOC}")


if __name__ == "__main__":
    main()
