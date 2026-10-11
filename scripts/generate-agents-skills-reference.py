#!/usr/bin/env python3
"""Generate the public agents and skills reference from source files."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "public" / "agents-skills-reference.md"
FIXTURE = ROOT / "docs" / "fixtures" / "agents-skills-reference-fixtures.json"
PUBLIC_BOOTSTRAP_GUIDE = "docs/public/bootstrap-report-guide.md"
PUBLIC_AGENT_EXCLUSIONS = {"skill-builder"}

HUMAN_ENTRY_COMMANDS = [
    "/aikit-bootstrap-project",
    "/implement-feature",
    "/design-implement",
    "/design-review",
    "/security-check",
]
PRIMARY_ENTRY_SKILLS = {
    "aikit-bootstrap-project",
    "implement-feature",
    "security-check",
}
OVERLAY_ENTRY_SKILLS = {
    "design-implement",
    "design-review",
    "setup-admin",
}
PUBLIC_INTERNAL_SKILL_ALLOWLIST = {"aikit-bootstrap-project"}
PUBLIC_BASE_SKILL_ALLOWLIST = {
    "analyze-mvp",
    "cross-check",
    "implement-mvp",
    "security-check",
    "write-ui-texts",
}
PUBLIC_BASE_AGENT_ALLOWLIST = {
    "cross-project-analyst",
    "mvp-analyst",
    "security-auditor",
    "tech-planner",
    "ux-writer",
}
VISIBLE_COMMAND_CONTRACT = [
    {
        "skill": "aikit-bootstrap-project",
        "command": "/aikit-bootstrap-project",
        "entry_class": "primary task entry",
        "use_it_when": "a repository is new or newly connected and discovery must happen before delivery.",
        "activates": "no delivery chain; it emits BOOTSTRAP_REPORT and the first recommended task prompt.",
    },
    {
        "skill": "implement-feature",
        "command": "/implement-feature",
        "entry_class": "primary task entry",
        "use_it_when": "ordinary implementation work starts after the task is known.",
        "activates": "architect -> coder -> tester -> reviewer for the selected profile.",
    },
    {
        "skill": "design-implement",
        "command": "/design-implement",
        "entry_class": "specialist overlay start",
        "use_it_when": "design is the primary input for implementation.",
        "activates": "a design bridge first, then the normal delivery chain.",
    },
    {
        "skill": "design-review",
        "command": "/design-review",
        "entry_class": "specialist overlay start",
        "use_it_when": "the task is review-first against a real design source.",
        "activates": "a design specialist instead of the full delivery chain.",
    },
    {
        "skill": "security-check",
        "command": "/security-check",
        "entry_class": "primary task entry",
        "use_it_when": "the task is a security, auth, secrets or dependency risk audit.",
        "activates": "the security-auditor review path.",
    },
]


def display_command(name: str) -> str:
    if name == "phase-forge":
        return "/phaseforge"
    return f"/{name}"


def entry_class_for(name: str) -> str:
    if name in PRIMARY_ENTRY_SKILLS:
        return "primary task entry"
    if name in OVERLAY_ENTRY_SKILLS:
        return "specialist overlay start"
    return "reference or advanced"


def parse_frontmatter(text: str) -> dict[str, Any]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    data: dict[str, Any] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            data[key] = [item.strip().strip("\"'") for item in value[1:-1].split(",") if item.strip()]
        else:
            data[key] = value.strip("\"'")
    return data


def owner_for(path: Path) -> tuple[str, str]:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    if parts[0] == "base":
        return "base", "base"
    if parts[0] == "profiles":
        return "profile", parts[1]
    if parts[0] == "packs":
        return "pack", parts[1]
    return "unknown", "unknown"


def public_profile_owner(owner: str) -> bool:
    manifest_path = ROOT / "profiles" / owner / "profile.manifest.json"
    if not manifest_path.exists():
        return True
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    visibility = manifest.get("visibility", {})
    if not isinstance(visibility, dict):
        visibility = {}
    return (
        visibility.get("scope") != "deprecated-demo-internal"
        and visibility.get("public_adoption_default") is not False
    )


def collect(kind: str) -> list[dict[str, Any]]:
    pattern = f"*/{kind}/*.md"
    files = sorted((ROOT / "base" / kind).glob("*.md"))
    files += sorted((ROOT / "profiles").glob(pattern))
    files += sorted((ROOT / "packs").glob(pattern))
    entries: list[dict[str, Any]] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(text)
        owner_type, owner = owner_for(path)
        name = str(frontmatter.get("name") or path.stem)
        if kind == "agents" and name in PUBLIC_AGENT_EXCLUSIONS:
            continue
        if owner_type == "base":
            if kind == "skills" and name not in PUBLIC_BASE_SKILL_ALLOWLIST:
                continue
            if kind == "agents" and name not in PUBLIC_BASE_AGENT_ALLOWLIST:
                continue
        if owner_type == "profile" and owner == "aikit-repo":
            if not (kind == "skills" and name in PUBLIC_INTERNAL_SKILL_ALLOWLIST):
                continue
            owner_type, owner = "public", "bootstrap"
        elif owner_type == "profile" and not public_profile_owner(owner):
            continue
        source = str(path.relative_to(ROOT))
        if owner_type == "public" and owner == "bootstrap" and kind == "skills":
            source = PUBLIC_BOOTSTRAP_GUIDE
        orchestrates = frontmatter.get("orchestrates", [])
        if not isinstance(orchestrates, list):
            orchestrates = []
        entries.append(
            {
                "name": name,
                "owner_type": owner_type,
                "owner": owner,
                "kind": kind[:-1],
                "source": source,
                "description": str(frontmatter.get("description") or "").strip(),
                "orchestrates": orchestrates,
                "entry_class": entry_class_for(name) if kind == "skills" else "reference or advanced",
                "human_entry": f"/{name}" in HUMAN_ENTRY_COMMANDS,
            }
        )
    return entries


def duplicate_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(str(entry["name"]) for entry in entries)
    duplicates = []
    for name in sorted(name for name, count in counts.items() if count > 1):
        owners = [f"{entry['owner_type']}:{entry['owner']}" for entry in entries if entry["name"] == name]
        duplicates.append({"name": name, "owners": owners})
    return duplicates


def table(entries: list[dict[str, Any]], columns: tuple[str, ...]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for entry in entries:
        values = []
        for column in columns:
            if column == "Name":
                values.append(f"`{entry['name']}`")
            elif column == "Owner":
                values.append(f"`{entry['owner_type']}:{entry['owner']}`")
            elif column == "Source":
                values.append(f"`{entry['source']}`")
            elif column == "Description":
                values.append(entry["description"] or "-")
            elif column == "Orchestrates":
                values.append(", ".join(f"`{item}`" for item in entry.get("orchestrates", [])) or "-")
            elif column == "Entry":
                values.append(str(entry.get("entry_class") or "reference or advanced"))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def render_doc(agents: list[dict[str, Any]], skills: list[dict[str, Any]], duplicates: list[dict[str, Any]]) -> str:
    lines = [
        "# Agents And Skills Reference",
        "",
        "This reference is generated from `base/`, `profiles/` and `packs/`. It is not the primary entry surface; start with `docs/index.html` for the generated start-working overview or `docs/public/start-here.md` for the task-first router, then use this page when you need to inspect available agents and skills.",
        "",
        "## Recommended Human Entry Commands",
        "",
        "Use these commands before direct agent mentions:",
        "",
        *[f"- `{command}`" for command in HUMAN_ENTRY_COMMANDS],
        "",
        "## Entry Surface Classes",
        "",
        "- `primary task entry` means the skill is a default task-first start after the user picks the task route.",
        "- `specialist overlay start` means the skill is only correct when the task is explicitly overlay-scoped and the canonical workflow or no-delivery status is still explained.",
        "- `reference or advanced` means the skill is not the first recommended start for a new task.",
        "",
        "## Visible Command Contract",
        "",
        "| Command | Entry | Use It When | Activates |",
        "| --- | --- | --- | --- |",
        *[
            f"| `{item['command']}` | `{item['entry_class']}` | {item['use_it_when']} | {item['activates']} |"
            for item in VISIBLE_COMMAND_CONTRACT
        ],
        "",
        "## Advanced Direct-Agent Usage",
        "",
        "Direct agent usage is advanced. Use it for narrow debugging, focused review or a known orchestration sub-role. For normal work, prefer the skill command because it owns routing, context, validation and stop conditions.",
        "",
        "## Agents",
        "",
        *table(agents, ("Name", "Owner", "Description", "Source")),
        "",
        "## Skills",
        "",
        *table(skills, ("Name", "Owner", "Entry", "Description", "Orchestrates", "Source")),
        "",
        "## Orchestrated Agents",
        "",
        "| Compatibility alias | Owner | Agents |",
        "| --- | --- | --- |",
    ]
    for skill in skills:
        if not skill.get("orchestrates"):
            continue
        agents_list = ", ".join(f"`{item}`" for item in skill["orchestrates"])
        lines.append(
            f"| `{display_command(str(skill['name']))}` | `{skill['owner_type']}:{skill['owner']}` | {agents_list} |"
        )
    lines.extend(
        [
            "",
            "> For Codex treat this table as compatibility-only aliases. The supported OpenAI/Codex surface is custom agents plus skills.",
            "",
            "## Duplicate Or Shadowed Names",
            "",
            "Duplicate names are allowed when a profile owns a domain-specific skill or agent, but they must be visible so users understand which profile owns the implementation.",
            "",
            "| Name | Owners |",
            "| --- | --- |",
        ]
    )
    for duplicate in duplicates:
        owners = ", ".join(f"`{owner}`" for owner in duplicate["owners"])
        lines.append(f"| `{duplicate['name']}` | {owners} |")
    lines.extend(
        [
            "",
            "## Validation",
            "",
            "```bash",
            "/aikit-docs --refresh agents-skills-reference",
            "/aikit-doctor --check validate-agents-skills-reference",
            "/aikit-doctor --check validate-documentation-integrity",
            "```",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    agents = collect("agents")
    skills = collect("skills")
    duplicates = duplicate_rows([*agents, *skills])
    entry_class_counts = Counter(str(skill["entry_class"]) for skill in skills)
    OUTPUT.write_text(render_doc(agents, skills, duplicates), encoding="utf-8")
    fixture = {
        "phase": "P72",
        "epic": "P72-E3",
        "doc": "docs/public/agents-skills-reference.md",
        "agents_count": len(agents),
        "skills_count": len(skills),
        "human_entry_commands": HUMAN_ENTRY_COMMANDS,
        "advanced_direct_agent_usage": True,
        "reference_is_primary_entry": False,
        "forbidden_markers": [
            "profiles/aikit-repo/skills/aikit-bootstrap-project.md",
        ],
        "forbidden_commands": [
            "/capture-memory",
            "/create-agent",
            "/create-skill",
            "/optimize-memory",
            "/workflow",
        ],
        "forbidden_agents": [
            "agent-builder",
            "memory-optimizer",
            "memory-writer",
            "workflow-runner",
        ],
        "entry_class_counts": dict(entry_class_counts),
        "entry_class_examples": [
            {"skill": "aikit-bootstrap-project", "entry_class": "primary task entry"},
            {"skill": "design-implement", "entry_class": "specialist overlay start"},
            {"skill": "write-ui-texts", "entry_class": "reference or advanced"},
        ],
        "visible_command_contract": VISIBLE_COMMAND_CONTRACT,
        "duplicates": duplicates,
        "orchestrated_skills": [
            {
                "name": skill["name"],
                "owner": f"{skill['owner_type']}:{skill['owner']}",
                "orchestrates": skill["orchestrates"],
            }
            for skill in skills
            if skill.get("orchestrates")
        ],
    }
    FIXTURE.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated {OUTPUT}")
    print(f"Updated {FIXTURE}")


if __name__ == "__main__":
    main()
