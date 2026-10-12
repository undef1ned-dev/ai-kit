#!/usr/bin/env python3
"""
Generate markdown profile summaries from profile/capability manifests.

Outputs:
- updates managed blocks in README.md
- rewrites docs/public/profiles-summary.md
- rewrites docs/public/compatibility-matrix.md
- rewrites docs/generated/index.html
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
PUBLIC_DOCS = ROOT / "docs" / "public"
SUMMARY_DOC = PUBLIC_DOCS / "profiles-summary.md"
COMPAT_DOC = PUBLIC_DOCS / "compatibility-matrix.md"
OVERVIEW_DOC = PUBLIC_DOCS / "aikit-overview.md"
INDEX_DOC = ROOT / "docs" / "generated" / "index.html"
ALIASES_DOC = ROOT / "docs" / "generated" / "agent-role-aliases.json"
LEGACY_INDEX_DOC = ROOT / "docs" / "index.html"
CONTINUITY_FIXTURE = ROOT / "docs" / "fixtures" / "continuity-brief-fixtures.json"
PRIMARY_START_ORDER = ["aikit-bootstrap-project", "implement-feature"]
OVERLAY_START_SKILLS = ["design-implement", "design-review", "setup-admin", "phase-forge", "northstar"]
PUBLIC_OPERATING_CLASSES = {"product-project"}


def display_command(name: str) -> str:
    if name == "phase-forge":
        return "/phaseforge"
    return f"/{name}"


VISIBLE_COMMANDS = [
    {
        "eyebrow": "Primary",
        "title": "<code>/aikit-bootstrap-project</code>",
        "body": "No-delivery-chain start for a newly connected repository. It finds the project shape and produces <code>BOOTSTRAP_REPORT</code>.",
    },
    {
        "eyebrow": "Primary",
        "title": "<code>/implement-feature</code>",
        "body": "Normal delivery entry for feature work. It usually activates <code>architect -> coder -> tester -> reviewer</code>.",
    },
    {
        "eyebrow": "Overlay",
        "title": "<code>/design-implement</code> and <code>/design-review</code>",
        "body": "Use these only when design is the primary input or the task is explicitly review-first against a design source.",
    },
    {
        "eyebrow": "Focused",
        "title": "<code>/security-check</code>",
        "body": "Use this when you need a security audit rather than ordinary implementation. It activates one specialist path, not the normal delivery chain.",
    },
]

START = "<!-- GENERATED:PROFILES_TABLE:START -->"
END = "<!-- GENERATED:PROFILES_TABLE:END -->"
START_SUMMARY = "<!-- GENERATED:PROFILES_SUMMARY:START -->"
END_SUMMARY = "<!-- GENERATED:PROFILES_SUMMARY:END -->"


def legacy_index_redirect_stub() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=./generated/index.html">
  <title>AIKit Docs Home Redirect</title>
</head>
<body>
  <p>Moved to <a href="./generated/index.html">docs/generated/index.html</a>.</p>
</body>
</html>
"""


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def continuity_surface() -> dict:
    data = read_json(CONTINUITY_FIXTURE)
    surface = data.get("aikit_repo_surface", {})
    return surface if isinstance(surface, dict) else {}


def profile_dirs() -> list[Path]:
    return sorted(path for path in (ROOT / "profiles").iterdir() if path.is_dir())


def collect_profiles() -> list[dict]:
    profiles = []
    for directory in profile_dirs():
        manifest_path = directory / "profile.manifest.json"
        capabilities_path = directory / "capabilities.json"
        if not manifest_path.exists():
            continue

        manifest = read_json(manifest_path)
        capabilities = read_json(capabilities_path) if capabilities_path.exists() else {"modes": []}

        agents = sorted(path.stem for path in (directory / "agents").glob("*.md"))
        skills = sorted(path.stem for path in (directory / "skills").glob("*.md"))
        profiles.append(
            {
                "name": manifest["profile"],
                "label": manifest["label"],
                "domain": manifest["domain"],
                "taxonomy": manifest.get("taxonomy", {}),
                "visibility": manifest.get("visibility", {}),
                "keywords": manifest.get("keywords", []),
                "path_signals": manifest.get("path_signals", []),
                "default_chain": manifest.get("default_chain", []),
                "recommended_packs": manifest.get("recommended_packs", []),
                "recommended_skills": manifest.get("recommended_skills", []),
                "agents": agents,
                "skills": skills,
                "modes": capabilities.get("modes", []),
            }
        )
    return profiles


def public_profiles(profiles: list[dict]) -> list[dict]:
    return [
        profile
        for profile in profiles
        if taxonomy_value(profile, "operating_class", "product-project") in PUBLIC_OPERATING_CLASSES
        and profile.get("visibility", {}).get("scope") != "deprecated-demo-internal"
        and profile.get("visibility", {}).get("public_adoption_default") is not False
    ]


def collect_adapters() -> list[dict]:
    adapters = []
    for path in sorted((ROOT / "adapters").glob("*/adapter.manifest.json")):
        data = read_json(path)
        adapters.append(
            {
                "name": path.parent.name,
                "runtime": data.get("runtime", ""),
                "label": data.get("label", ""),
                "status": data.get("status", ""),
                "entrypoint_style": data.get("entrypoint_style", ""),
                "install_type": data.get("install_type", ""),
                "memory_path": data.get("memory_path", ""),
                "continuation": bool(data.get("continuation_prompt")),
                "runtime_entrypoints": data.get("runtime_entrypoints", []),
                "graph_execution": data.get("graph_execution", {}),
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


def taxonomy_value(profile: dict, field: str, default: object = "") -> object:
    taxonomy = profile.get("taxonomy", {})
    if not isinstance(taxonomy, dict):
        return default
    return taxonomy.get(field, default)


def derive_entry_paths(profile: dict) -> dict[str, str]:
    skills = set(profile["skills"])

    def first_existing(*names: str) -> str:
        for name in names:
            if name in skills:
                return f"`/{name}`"
        return "`inspect-chain`"

    return {
        "new-artifact": first_existing(
            "new-page",
            "new-component",
            "new-composable",
            "new-store",
            "new-server-route",
            "new-feature",
            "new-screen",
            "new-router",
            "new-app",
            "implement-feature",
        ),
        "small-patch": first_existing("implement-feature"),
        "feature-work": first_existing("implement-feature", "implement-mvp"),
        "test-only": first_existing("add-tests"),
        "review-only": first_existing("design-review"),
    }


def primary_start_for_profile(profile: dict) -> str:
    skills = set(profile["skills"])
    for name in PRIMARY_START_ORDER:
        if name in skills:
            return f"`{display_command(name)}`"
    return "—"


def overlay_starts_for_profile(profile: dict) -> list[str]:
    skills = set(profile["skills"])
    return [f"`{display_command(name)}`" for name in OVERLAY_START_SKILLS if name in skills]


def start_contract_for_profile(profile: dict) -> str:
    primary = primary_start_for_profile(profile)
    if primary == "`/aikit-bootstrap-project`":
        return "Bootstrap is a no-delivery-chain start; choose a bounded overlay or repo delivery chain only after discovery."
    return "Choose one primary start or one bounded overlay start; overlays do not replace the default chain."


def continuity_entry_lines(profile: dict) -> list[str]:
    if profile.get("name") != "aikit-repo":
        return []
    surface = continuity_surface()
    return [
        f"- Continuity start: `{surface.get('primary_resume_command', '/aikit-run-task --resume-from-bundle <bundle-or-journal> --json')}`",
        f"- Continuity fallback: `{surface.get('fresh_start_command', '/aikit-run-task --task \"<task>\" --profile aikit-repo --json')}`",
        "- Continuity explorer: `/aikit-knowledge-refresh --context-pack --task \"<task>\" --profile aikit-repo --json` with trust-labeled `index -> timeline -> details` progression",
        f"- Memory Inbox: `{surface.get('inbox_command', '/aikit-command-center memory-inbox --json')}` for local-first review of recent observations, pending promotions, blocked captures and ledger history.",
        "- Explorer search keeps `review-required` visible by default, while raw and stale stay inspect-only until deeper drilldown is explicitly requested.",
    ]


def public_specialized_roles(profile: dict) -> list[str]:
    roles = taxonomy_value(profile, "specialized_role_set", [])
    if not isinstance(roles, list):
        return []
    return [str(role) for role in roles if str(role) not in {"skill-builder"}]


def public_global_roles(profile: dict) -> list[str]:
    roles = taxonomy_value(profile, "global_role_set", [])
    if not isinstance(roles, list):
        return []
    return [str(role) for role in roles if str(role) not in {"memory-writer"}]


def public_role_aliases(profile: dict) -> list[tuple[str, str]]:
    aliases = taxonomy_value(profile, "role_aliases", {})
    if not isinstance(aliases, dict):
        return []
    return [
        (str(role), str(agent_id))
        for role, agent_id in sorted(aliases.items())
        if str(role) not in {"skill-builder"} and str(agent_id) not in {"skill-builder"}
    ]


def replace_block(text: str, start: str, end: str, content: str) -> str:
    if start not in text or end not in text:
        raise ValueError(f"Managed block markers not found: {start} / {end}")
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    return before + start + "\n" + content.rstrip() + "\n" + end + after


def generate_readme_table(profiles: list[dict]) -> str:
    lines = [
        "| Профиль | Direction | Ecosystem | Framework | Domain family | Primary start | Overlay starts | Default chain |",
        "|---------|-----------|-----------|-----------|---------------|---------------|----------------|---------------|",
    ]
    for profile in profiles:
        chain = " -> ".join(profile["default_chain"])
        primary = primary_start_for_profile(profile)
        overlays = ", ".join(overlay_starts_for_profile(profile)) or "—"
        lines.append(
            f"| `{profile['name']}` | `{taxonomy_value(profile, 'direction', '—')}` | `{taxonomy_value(profile, 'ecosystem', '—')}` | `{taxonomy_value(profile, 'framework', '—')}` | `{taxonomy_value(profile, 'domain_family', profile['domain'])}` | {primary} | {overlays} | `{chain}` |"
        )
    return "\n".join(lines)


def generate_readme_summary(profiles: list[dict]) -> str:
    blocks = []
    for profile in profiles:
        entry_paths = derive_entry_paths(profile)
        modes = ", ".join(f"`{mode['name']}`" for mode in profile["modes"])
        packs = ", ".join(f"`{pack}`" for pack in profile["recommended_packs"]) or "—"
        recommended_skills = ", ".join(f"`{skill}`" for skill in profile["recommended_skills"]) or "—"
        entry_paths_line = ", ".join(f"`{intent}` → {entry}" for intent, entry in entry_paths.items())
        primary_start = primary_start_for_profile(profile)
        overlay_starts = ", ".join(overlay_starts_for_profile(profile)) or "—"
        blocks.append(
            "\n".join(
                [
                    f"### `{profile['name']}` — {profile['label']}",
                    f"- Operating class: `{taxonomy_value(profile, 'operating_class', 'product-project')}`",
                    f"- Direction: `{taxonomy_value(profile, 'direction', '—')}`",
                    f"- Ecosystem: `{taxonomy_value(profile, 'ecosystem', '—')}`",
                    f"- Framework: `{taxonomy_value(profile, 'framework', '—')}`",
                    f"- Domain family: `{taxonomy_value(profile, 'domain_family', profile['domain'])}`",
                    f"- Stack profile: `{taxonomy_value(profile, 'stack_profile', profile['name'])}`",
                    f"- Legacy domain: `{profile['domain']}`",
                    f"- Default chain: `{ ' -> '.join(profile['default_chain']) }`",
                    f"- Core roles: {', '.join(f'`{item}`' for item in taxonomy_value(profile, 'core_role_set', [])) or '—'}",
                    f"- Capability modes: {modes}",
                    f"- Path signals: {', '.join(f'`{item}`' for item in profile['path_signals'])}",
                    f"- Рекомендуемые паки: {packs}",
                    f"- Рекомендуемые скиллы: {recommended_skills}",
                    f"- Primary start: {primary_start}",
                    f"- Overlay starts: {overlay_starts}",
                    f"- Start contract: {start_contract_for_profile(profile)}",
                    f"- Recommended entry paths: {entry_paths_line}",
                    *continuity_entry_lines(profile),
                ]
            )
        )
    return "\n\n".join(blocks)


def generate_summary_doc(profiles: list[dict]) -> str:
    sections = [
        "# Профили — Structured Summary",
        "",
        "Этот документ генерируется из `profile.manifest.json` и `capabilities.json`.",
        "Он дополняет ручную документацию, но не заменяет её.",
        "",
        "## Direction Model",
        "",
        "Profiles are grouped as `direction -> ecosystem -> framework` while source folders remain flat for installer compatibility.",
        "",
    ]
    for profile in profiles:
        entry_paths = derive_entry_paths(profile)
        primary_start = primary_start_for_profile(profile)
        overlay_starts = ", ".join(overlay_starts_for_profile(profile)) or "—"
        role_alias_lines = [f"- `{role}` → `{agent_id}`" for role, agent_id in public_role_aliases(profile)] or ["- —"]
        sections.extend(
            [
                f"## {profile['label']} (`{profile['name']}`)",
                "",
                f"- Operating class: `{taxonomy_value(profile, 'operating_class', 'product-project')}`",
                f"- Direction: `{taxonomy_value(profile, 'direction', '—')}`",
                f"- Ecosystem: `{taxonomy_value(profile, 'ecosystem', '—')}`",
                f"- Framework: `{taxonomy_value(profile, 'framework', '—')}`",
                f"- Domain family: `{taxonomy_value(profile, 'domain_family', profile['domain'])}`",
                f"- Stack profile: `{taxonomy_value(profile, 'stack_profile', profile['name'])}`",
                f"- Legacy domain: `{profile['domain']}`",
                f"- Default chain: `{ ' -> '.join(profile['default_chain']) }`",
                f"- Core roles: {', '.join(f'`{item}`' for item in taxonomy_value(profile, 'core_role_set', [])) or '—'}",
                f"- Specialized roles: {', '.join(f'`{item}`' for item in public_specialized_roles(profile)) or '—'}",
                f"- Global roles: {', '.join(f'`{item}`' for item in public_global_roles(profile)) or '—'}",
                f"- Workflow contract: `{((taxonomy_value(profile, 'workflow_contract', {}) or {}).get('domain_contract', '—'))}` / `{((taxonomy_value(profile, 'workflow_contract', {}) or {}).get('stack_specialization', '—'))}`",
                f"- Path signals: {', '.join(f'`{item}`' for item in profile['path_signals'])}",
                f"- Keywords: {', '.join(f'`{item}`' for item in profile['keywords'])}",
                f"- Рекомендуемые паки: {', '.join(f'`{item}`' for item in profile['recommended_packs']) or '—'}",
                f"- Рекомендуемые скиллы: {', '.join(f'`{item}`' for item in profile['recommended_skills']) or '—'}",
                f"- Primary start: {primary_start}",
                f"- Overlay starts: {overlay_starts}",
                f"- Start contract: {start_contract_for_profile(profile)}",
                f"- Special surfaces: {', '.join(f'`{item}`' for item in taxonomy_value(profile, 'special_surfaces', [])) or '—'}",
                *continuity_entry_lines(profile),
                "",
                "### Recommended Entry Paths",
                "",
                *[f"- `{intent}` → {entry}" for intent, entry in entry_paths.items()],
                "",
                "### Role Aliases",
                "",
                *role_alias_lines,
                "",
                "### Capability Modes",
                "",
            ]
        )
        for mode in profile["modes"]:
            sections.extend(
                [
                    f"- `{mode['name']}`",
                    f"  Globs: {', '.join(f'`{item}`' for item in mode['file_globs'])}",
                    f"  Owned by: {', '.join(f'`{item}`' for item in mode['owned_by'])}",
                    f"  Suggested skills: {', '.join(f'`{item}`' for item in mode.get('suggested_skills', [])) or '—'}",
                    f"  Focus: {', '.join(mode['focus'])}",
                ]
            )
        sections.append("")
    return "\n".join(sections).rstrip() + "\n"


def generate_compatibility_doc(profiles: list[dict], adapters: list[dict], presets: list[dict], deprecated: list[dict]) -> str:
    lines = [
        "# Compatibility Matrix",
        "",
        "Этот документ генерируется из profile, adapter и preset manifests.",
        "Он показывает, что именно в AIKit уже готово как продуктовая поверхность.",
        "",
        "## Runtime Adapters",
        "",
        "| Adapter | Runtime | Status | Install | Continuation | Runtime entrypoints | Graph execution | Parallel handoff | Memory path |",
        "|---------|---------|--------|---------|--------------|---------------------|-----------------|------------------|-------------|",
    ]
    for adapter in adapters:
        install = adapter["install_type"] or "—"
        continuation = "yes" if adapter["continuation"] else "no"
        entrypoints = str(len(adapter["runtime_entrypoints"])) if adapter["runtime_entrypoints"] else "0"
        graph_execution = adapter["graph_execution"] if isinstance(adapter["graph_execution"], dict) else {}
        graph_status = graph_execution.get("status", "—")
        parallel = "yes" if graph_execution.get("supports_parallel_handoff") else "no"
        lines.append(
            f"| `{adapter['name']}` | `{adapter['runtime']}` | `{adapter['status']}` | `{install}` | `{continuation}` | `{entrypoints}` | `{graph_status}` | `{parallel}` | `{adapter['memory_path']}` |"
        )

    lines.extend(
        [
            "",
            "## Profiles",
            "",
            "| Profile | Operating class | Direction | Ecosystem | Framework | Domain family | Legacy domain | Modes | Skills | Recommended packs |",
            "|---------|-----------------|-----------|-----------|-----------|---------------|---------------|-------|--------|-------------------|",
        ]
    )
    for profile in profiles:
        lines.append(
            f"| `{profile['name']}` | `{taxonomy_value(profile, 'operating_class', 'product-project')}` | `{taxonomy_value(profile, 'direction', '—')}` | `{taxonomy_value(profile, 'ecosystem', '—')}` | `{taxonomy_value(profile, 'framework', '—')}` | `{taxonomy_value(profile, 'domain_family', profile['domain'])}` | `{profile['domain']}` | `{len(profile['modes'])}` | `{len(profile['skills'])}` | {', '.join(f'`{p}`' for p in profile['recommended_packs']) or '—'} |"
        )

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
        profiles_value = ", ".join(f"`{item}`" for item in preset["profiles"]) or "—"
        packs_value = ", ".join(f"`{item}`" for item in preset["packs"]) or "—"
        adapter_value = f"`{preset['recommended_adapter']}`" if preset["recommended_adapter"] else "—"
        lines.append(f"| `{preset['name']}` | {profiles_value} | {packs_value} | {adapter_value} |")

    if deprecated:
        lines.extend(
            [
                "",
                "## Deprecated Preset Archive",
                "",
                "These presets remain source-resolvable for compatibility but are not supported public defaults.",
                "",
                "| Preset | Profiles | Status | Migration note |",
                "|--------|----------|--------|----------------|",
            ]
        )
        for preset in deprecated:
            lifecycle = preset.get("lifecycle", {})
            profiles_value = ", ".join(f"`{item}`" for item in preset["profiles"]) or "—"
            lines.append(
                f"| `{preset['name']}` | {profiles_value} | `deprecated` | {lifecycle.get('replacement_guidance', 'create a project-specific profile before new adoption')} |"
            )

    return "\n".join(lines).rstrip() + "\n"


def generate_docs_home(profiles: list[dict], adapters: list[dict], presets: list[dict]) -> str:
    active_adapters = [adapter for adapter in adapters if adapter["status"] == "active"]
    active_non_claude = [adapter for adapter in active_adapters if adapter["runtime"] != "claude"]
    profile_cards = "\n".join(
        f"""
      <div class="card">
        <div class="eyebrow">Profile</div>
        <h3>{profile['label']}</h3>
        <p>{taxonomy_value(profile, 'direction', '—')} · {taxonomy_value(profile, 'ecosystem', '—')} · {taxonomy_value(profile, 'framework', '—')}</p>
        <div class="meta">{taxonomy_value(profile, 'domain_family', profile['domain'])} · {taxonomy_value(profile, 'stack_profile', profile['name'])}</div>
        <div class="meta">{len(profile['modes'])} modes · {len(profile['skills'])} skills · primary {primary_start_for_profile(profile)}</div>
        <div class="meta">Overlay starts: {", ".join(overlay_starts_for_profile(profile)) or "—"}</div>
      </div>"""
        for profile in profiles
    )
    adapter_cards = "\n".join(
        f"""
      <div class="card">
        <div class="eyebrow">Adapter</div>
        <h3>{adapter['label']}</h3>
        <p>{adapter['runtime']}</p>
        <div class="meta">{adapter['status']} · {adapter['install_type'] or 'no install flow'} · {len(adapter['runtime_entrypoints'])} entrypoints</div>
      </div>"""
        for adapter in adapters
    )
    preset_cards = "\n".join(
        f"""
      <div class="card">
        <div class="eyebrow">Preset</div>
        <h3>{preset['label']}</h3>
        <p>{preset['description']}</p>
        <div class="meta">{preset['recommended_adapter']} · {len(preset['profiles'])} profiles</div>
      </div>"""
        for preset in presets
    )
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AIKit — Docs Home</title>
  <style>
    :root {{
      --bg: #f6f3ee;
      --surface: #fffdf9;
      --ink: #1d1b1a;
      --muted: #6a645f;
      --accent: #bb4d00;
      --line: #e7ded3;
      --shadow: 0 12px 30px rgba(70, 52, 37, 0.08);
      --radius: 18px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "SF Pro Display", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(187, 77, 0, 0.08), transparent 28%),
        linear-gradient(180deg, #fcfaf6 0%, var(--bg) 100%);
      color: var(--ink);
    }}
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 40px 24px 72px; }}
    .hero {{
      background: rgba(255,255,255,0.65);
      backdrop-filter: blur(14px);
      border: 1px solid var(--line);
      border-radius: 28px;
      padding: 32px;
      box-shadow: var(--shadow);
      margin-bottom: 28px;
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: .08em;
      font-size: 12px;
      color: var(--accent);
      font-weight: 700;
      margin-bottom: 10px;
    }}
    h1 {{ font-size: 42px; line-height: 1.05; margin: 0 0 12px; }}
    .lead {{ color: var(--muted); font-size: 18px; line-height: 1.6; max-width: 760px; }}
    .hero-actions, .link-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }}
    .action, .card {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 18px;
      box-shadow: var(--shadow);
    }}
    .action {{
      text-decoration: none;
      color: inherit;
      transition: transform .15s ease, border-color .15s ease;
    }}
    .action:hover {{ transform: translateY(-2px); border-color: var(--accent); }}
    .action strong {{ display: block; margin-bottom: 8px; font-size: 16px; }}
    .action span, .meta, .card p {{ color: var(--muted); line-height: 1.5; }}
    .pill-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }}
    .pill {{
      background: rgba(187, 77, 0, 0.08);
      border: 1px solid rgba(187, 77, 0, 0.14);
      border-radius: 999px;
      padding: 8px 12px;
      color: var(--ink);
      font-size: 13px;
    }}
    .section {{ margin-top: 30px; }}
    .section h2 {{ font-size: 24px; margin: 0 0 12px; }}
    .section-copy {{ color: var(--muted); margin: 0 0 16px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }}
    .card h3 {{ margin: 0 0 8px; font-size: 18px; }}
    .snapshot {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin: 22px 0 0;
    }}
    .metric {{
      background: rgba(255,255,255,0.55);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 16px;
    }}
    .metric strong {{ display: block; font-size: 28px; margin-bottom: 6px; }}
    .metric span {{ color: var(--muted); font-size: 13px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="eyebrow">AIKit</div>
      <h1>One entry flow for developer work</h1>
      <p class="lead">AIKit should let a developer start work without decoding repository internals first: connect or install the runtime, run bootstrap, choose one slash command, and let the selected workflow activate the right profile and agents.</p>
      <div class="pill-row">
        <div class="pill">{len(active_non_claude)} active non-Claude runtimes</div>
        <div class="pill">{len(presets)} curated presets</div>
        <div class="pill">{sum(len(p['skills']) for p in profiles)} profile skills</div>
      </div>
      <div class="snapshot">
        <div class="metric"><strong>{len(profiles)}</strong><span>profiles</span></div>
        <div class="metric"><strong>{len(adapters)}</strong><span>runtime adapters</span></div>
        <div class="metric"><strong>{len(active_adapters)}</strong><span>active runtimes</span></div>
        <div class="metric"><strong>{len(presets)}</strong><span>team presets</span></div>
        <div class="metric"><strong>{sum(len(p['skills']) for p in profiles)}</strong><span>profile skills</span></div>
      </div>
    </section>

    <section class="section">
      <h2>Start Working</h2>
      <p class="section-copy">Use this order first: attach or install AIKit, run bootstrap, choose one command, then inspect reference docs only when needed.</p>
      <div class="cards">
        <div class="card">
          <div class="eyebrow">Step 1</div>
          <h3>Attach or install</h3>
          <p>Pick a preset and connect AIKit to a project, or install a Codex/OpenCode workspace.</p>
          <div class="meta">Open: <a href="../public/get-started.md">Get Started</a> → <a href="../public/install-matrix.md">Install Matrix</a></div>
        </div>
        <div class="card">
          <div class="eyebrow">Step 2</div>
          <h3>Run bootstrap</h3>
          <p>Start every newly connected repository with <code>/aikit-bootstrap-project</code> and read the emitted <code>BOOTSTRAP_REPORT</code>.</p>
          <div class="meta">Open: <a href="../public/start-here.md">Start Here</a></div>
        </div>
        <div class="card">
          <div class="eyebrow">Step 3</div>
          <h3>Choose one command</h3>
          <p>Use <code>/implement-feature</code>, <code>/design-implement</code>, <code>/design-review</code>, or <code>/security-check</code> based on the job.</p>
          <div class="meta">Open: <a href="../public/start-here.md">Start Here</a> → <a href="../public/agents-skills-reference.md">Agents & Skills</a></div>
        </div>
        <div class="card">
          <div class="eyebrow">Step 4</div>
          <h3>Understand the active chain</h3>
          <p>Normal delivery work activates <code>architect -> coder -> tester -> reviewer</code>; focused follow-up commands and expert overlays stay bounded and explicit, while profile-local overlays stay inside the selected profile reference.</p>
          <div class="meta">Open: <a href="../public/profiles-summary.md">Profiles Summary</a> → <a href="./catalog.html">HTML Catalog</a></div>
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Start surfaces</h2>
      <p class="section-copy">These are the four surfaces that carry the first-run story. Use them before you open broader browse or platform documentation.</p>
      <div class="cards">
        <div class="card">
          <div class="eyebrow">Start surface</div>
          <h3>Get Started</h3>
          <p>Attach or install AIKit, choose a preset, and understand which runtime path fits the project.</p>
          <div class="meta">Open: <a href="../public/get-started.md">Get Started</a></div>
        </div>
        <div class="card">
          <div class="eyebrow">Start surface</div>
          <h3>Start Here</h3>
          <p>Run bootstrap, read <code>BOOTSTRAP_REPORT</code>, choose exactly one working command, then let the selected workflow route the task.</p>
          <div class="meta">Open: <a href="../public/start-here.md">Start Here</a></div>
        </div>
        <div class="card">
          <div class="eyebrow">Start surface</div>
          <h3>Profiles Summary</h3>
          <p>Check primary starts, bounded overlays, capability modes and default chains after the task route is already known.</p>
          <div class="meta">Open: <a href="../public/profiles-summary.md">Profiles Summary</a></div>
        </div>
        <div class="card">
          <div class="eyebrow">Reference surface</div>
          <h3>Agents &amp; Skills</h3>
          <p>Inspect which commands and agents exist only after the first task route is clear and you need reference detail.</p>
          <div class="meta">Open: <a href="../public/agents-skills-reference.md">Agents &amp; Skills</a></div>
        </div>
      </div>
      <p class="section-copy">Use these surfaces only after the four-step start flow above is clear.</p>
      <div class="hero-actions">
        <a class="action" href="../public/product-story.md"><strong>Product Story</strong><span>Use-case карта AIKit: кому и зачем нужен каждый surface, и какой next step делать дальше.</span></a>
        <a class="action" href="./catalog.html"><strong>HTML Catalog</strong><span>Агенты, skills, profile summary и workflow playbook в одной странице.</span></a>
        <a class="action" href="../public/release-center.md"><strong>Release Center</strong><span>Текущая версия, unreleased state и release workflow AIKit.</span></a>
        <a class="action" href="../public/install-matrix.md"><strong>Install Matrix</strong><span>Runtime install surface, preset bundles и основные install команды.</span></a>
        <a class="action" href="../public/runtime-maturity-review.md"><strong>Runtime Maturity Review</strong><span>Текущий verdict по Codex и OpenCode с критериями promotion.</span></a>
        <a class="action" href="../public/opencode-runtime-guide.md"><strong>OpenCode Runtime Guide</strong><span>Practical local OpenCode start, continue, validate and troubleshoot flow.</span></a>
        <a class="action" href="../public/compatibility-matrix.md"><strong>Compatibility Matrix</strong><span>Runtime adapters, presets и текущее покрытие платформы.</span></a>
        <a class="action" href="../public/marketplace.md"><strong>Marketplace</strong><span>Curated registry surface для packs, presets и runtime adapters.</span></a>
        <a class="action" href="../public/publishing-workflow.md"><strong>Publishing Workflow</strong><span>Distribution channels и eligibility path для packs, presets и adapters.</span></a>
      </div>
    </section>

    <section class="section">
      <h2>Recommended journeys</h2>
      <p class="section-copy">Вместо того чтобы читать всё подряд, начни с одного понятного пути.</p>
      <div class="cards">
        <div class="card">
          <div class="eyebrow">Journey</div>
          <h3>Roll out in an existing project</h3>
          <p>Для production-ready внедрения AIKit через attach or install, затем bootstrap, затем один рабочий slash command.</p>
          <div class="meta">Open: <a href="../public/get-started.md">Get Started</a> → <a href="../public/start-here.md">Start Here</a> → <a href="../public/install-matrix.md">Install Matrix</a></div>
        </div>
        <div class="card">
          <div class="eyebrow">Journey</div>
          <h3>Adopt multiple runtimes</h3>
          <p>Для Codex / OpenCode adoption без переписывания core workflows и profile logic.</p>
          <div class="meta">Open: <a href="../public/product-story.md">Product Story</a> → <a href="../public/runtime-maturity-review.md">Runtime Review</a> → <a href="../public/opencode-runtime-guide.md">OpenCode Guide</a></div>
        </div>
        <div class="card">
          <div class="eyebrow">Journey</div>
          <h3>Choose a team bundle</h3>
          <p>Для быстрого выбора preset, profile and primary command model под конкретную domain-команду.</p>
          <div class="meta">Open: <a href="../public/get-started.md">Get Started</a> → <a href="../public/profiles-summary.md">Profiles Summary</a> → <a href="../public/agents-skills-reference.md">Agents & Skills</a></div>
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Command Model</h2>
      <p class="section-copy">These are the global visible commands a developer should understand before diving into internal reference docs. Profile-specific overlays such as <code>/setup-admin</code> show up only after the task and profile are known.</p>
      <div class="cards">{''.join(f'<div class="card"><div class="eyebrow">{item["eyebrow"]}</div><h3>{item["title"]}</h3><p>{item["body"]}</p></div>' for item in VISIBLE_COMMANDS)}</div>
    </section>

    <section class="section">
      <h2>Runtime adapters</h2>
      <p class="section-copy">Current execution surface for Claude, Codex and OpenCode.</p>
      <div class="cards">{adapter_cards}</div>
    </section>

    <section class="section">
      <h2>Profiles</h2>
      <p class="section-copy">Основные доменные профили AIKit с capability coverage и skill surface.</p>
      <div class="cards">{profile_cards}</div>
    </section>

    <section class="section">
      <h2>Presets</h2>
      <p class="section-copy">Готовые team bundles для более дешёвого onboarding и install flow.</p>
      <div class="cards">{preset_cards}</div>
    </section>
  </div>
</body>
</html>
"""


def generate_aliases_doc(profiles: list[dict]) -> str:
    alias_rows = []
    for profile in profiles:
        taxonomy = profile.get("taxonomy", {})
        role_aliases = taxonomy.get("role_aliases", {}) if isinstance(taxonomy, dict) else {}
        if not isinstance(role_aliases, dict):
            role_aliases = {}
        for role, agent_id in sorted(role_aliases.items()):
            alias_rows.append(
                {
                    "profile": profile["name"],
                    "domain_family": taxonomy.get("domain_family", profile["domain"]),
                    "stack_profile": taxonomy.get("stack_profile", profile["name"]),
                    "role": role,
                    "legacy_agent_id": agent_id,
                }
            )
    return json.dumps({"aliases": alias_rows}, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    profiles = collect_profiles()
    public_profile_set = public_profiles(profiles)
    adapters = collect_adapters()
    presets = collect_presets()
    public_preset_set = public_presets(presets)
    deprecated_preset_set = deprecated_presets(presets)

    readme = README.read_text(encoding="utf-8")
    if START in readme and END in readme:
        readme = replace_block(readme, START, END, generate_readme_table(public_profile_set))
    if START_SUMMARY in readme and END_SUMMARY in readme:
        readme = replace_block(readme, START_SUMMARY, END_SUMMARY, generate_readme_summary(public_profile_set))
    README.write_text(readme, encoding="utf-8")

    overview = OVERVIEW_DOC.read_text(encoding="utf-8")
    if START in overview and END in overview:
        overview = replace_block(overview, START, END, generate_readme_table(public_profile_set))
    if START_SUMMARY in overview and END_SUMMARY in overview:
        overview = replace_block(overview, START_SUMMARY, END_SUMMARY, generate_readme_summary(public_profile_set))
    OVERVIEW_DOC.write_text(overview, encoding="utf-8")

    SUMMARY_DOC.write_text(generate_summary_doc(public_profile_set), encoding="utf-8")
    COMPAT_DOC.write_text(generate_compatibility_doc(public_profile_set, adapters, public_preset_set, deprecated_preset_set), encoding="utf-8")
    INDEX_DOC.parent.mkdir(parents=True, exist_ok=True)
    INDEX_DOC.write_text(generate_docs_home(public_profile_set, adapters, public_preset_set), encoding="utf-8")
    ALIASES_DOC.write_text(generate_aliases_doc(profiles), encoding="utf-8")
    LEGACY_INDEX_DOC.write_text(legacy_index_redirect_stub(), encoding="utf-8")

    print(f"Updated {README}")
    print(f"Updated {OVERVIEW_DOC}")
    print(f"Updated {SUMMARY_DOC}")
    print(f"Updated {COMPAT_DOC}")
    print(f"Updated {INDEX_DOC}")
    print(f"Updated {ALIASES_DOC}")
    print(f"Updated {LEGACY_INDEX_DOC}")


if __name__ == "__main__":
    main()
