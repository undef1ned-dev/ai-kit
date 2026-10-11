#!/usr/bin/env python3
"""
Generate docs/generated/catalog.html — a single-page HTML catalog of all agents and skills.

Usage:
    python scripts/generate-catalog.py
    python scripts/generate-catalog.py --root /path/to/claude-config --out docs/generated/catalog.html
"""

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path

PRIMARY_START_ORDER = ['aikit-bootstrap-project', 'implement-feature']
OVERLAY_START_SKILLS = ['design-implement', 'design-review', 'setup-admin']
PRIMARY_ENTRY_SKILLS = {'aikit-bootstrap-project', 'implement-feature', 'security-check'}
OVERLAY_ENTRY_SKILLS = {'design-implement', 'design-review', 'setup-admin'}
NO_DELIVERY_START_SKILLS = {'aikit-bootstrap-project'}
PUBLIC_BASE_EXCLUSIONS = {'aikit-maintainer', 'improve-aikit', 'memory-status'}
PUBLIC_PROFILE_EXCLUSIONS = {'aikit-repo'}
PUBLIC_AGENT_EXCLUSIONS = {'skill-builder'}
PUBLIC_BASE_SKILL_ALLOWLIST = {
    'analyze-mvp',
    'cross-check',
    'implement-mvp',
    'security-check',
    'write-ui-texts',
}
PUBLIC_BASE_AGENT_ALLOWLIST = {
    'cross-project-analyst',
    'mvp-analyst',
    'security-auditor',
    'tech-planner',
    'ux-writer',
}
VISIBLE_COMMAND_OVERVIEW = [
    {
        'command': '/aikit-bootstrap-project',
        'entry': 'primary task entry',
        'activates': 'BOOTSTRAP_REPORT, no-delivery-chain start',
    },
    {
        'command': '/implement-feature',
        'entry': 'primary task entry',
        'activates': 'architect -> coder -> tester -> reviewer',
    },
    {
        'command': '/design-implement',
        'entry': 'specialist overlay start',
        'activates': 'design bridge + delivery chain',
    },
    {
        'command': '/design-review',
        'entry': 'specialist overlay start',
        'activates': 'design specialist review path',
    },
    {
        'command': '/security-check',
        'entry': 'primary task entry',
        'activates': 'security-auditor review path',
    },
]


def display_command(name: str) -> str:
    if name == 'phase-forge':
        return '/phaseforge'
    return f'/{name}'

# ─── Frontmatter parsing ────────────────────────────────────────────────────

def parse_frontmatter(text: str) -> dict:
    """Extract YAML-like frontmatter from a markdown file (no external deps)."""
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m:
        return {}
    raw = m.group(1)
    result = {}
    for line in raw.splitlines():
        line = line.rstrip()
        if not line or line.startswith('#'):
            continue
        kv = re.match(r'^(\w[\w-]*):\s*(.*)', line)
        if not kv:
            continue
        key, val = kv.group(1), kv.group(2).strip()
        # Quoted string
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        elif val.startswith("'") and val.endswith("'"):
            val = val[1:-1]
        # Inline list: ["a", "b"] or ['a', 'b']
        elif val.startswith('[') and val.endswith(']'):
            inner = val[1:-1]
            items = [i.strip().strip('"').strip("'") for i in inner.split(',') if i.strip()]
            val = items
        result[key] = val
    return result


def read_md_files(directory: Path, kind: str) -> list[dict]:
    """Read all .md files in directory and return list of parsed entries."""
    entries = []
    if not directory.exists():
        return entries
    for md in sorted(directory.glob('*.md')):
        text = md.read_text(encoding='utf-8')
        fm = parse_frontmatter(text)
        if not fm.get('name'):
            fm['name'] = md.stem
        if kind == 'agent' and fm.get('name') in PUBLIC_AGENT_EXCLUSIONS:
            continue
        fm['_kind'] = kind
        fm['_file'] = str(md)
        entries.append(fm)
    return entries


def read_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def is_public_profile(root: Path, profile_name: str) -> bool:
    if profile_name in PUBLIC_PROFILE_EXCLUSIONS:
        return False
    manifest = read_json_file(root / 'profiles' / profile_name / 'profile.manifest.json')
    visibility = manifest.get('visibility', {})
    if not isinstance(visibility, dict):
        visibility = {}
    return (
        visibility.get('scope') != 'deprecated-demo-internal'
        and visibility.get('public_adoption_default') is not False
    )


# ─── Data collection ────────────────────────────────────────────────────────

def collect_data(root: Path) -> dict:
    """Collect all agents and skills grouped by section."""
    sections = {}

    # Base
    sections['base'] = {
        'label': 'Base',
        'color': '#2196F3',
        'description': 'Доступны во всех профилях',
        'agents': [
            entry
            for entry in read_md_files(root / 'base' / 'agents', 'agent')
            if entry.get('name') in PUBLIC_BASE_AGENT_ALLOWLIST
        ],
        'skills': [
            entry
            for entry in read_md_files(root / 'base' / 'skills', 'skill')
            if entry.get('name') in PUBLIC_BASE_SKILL_ALLOWLIST
        ],
    }

    # Profiles
    profile_meta = {
        'vue-nuxt':       {'label': 'Vue Nuxt',       'color': '#00C58E', 'stack': 'Vue 3, Nuxt 3, Pinia, VueUse'},
        'python-django':  {'label': 'Python Django',  'color': '#092E20', 'stack': 'Django 5.x, DRF, Admin'},
        'python-fastapi': {'label': 'Python FastAPI', 'color': '#009688', 'stack': 'FastAPI 0.115+, SQLAlchemy 2.0, LangGraph'},
    }
    profiles_dir = root / 'profiles'
    if profiles_dir.exists():
        for profile_name, meta in profile_meta.items():
            if not is_public_profile(root, profile_name):
                continue
            p = profiles_dir / profile_name
            agents = read_md_files(p / 'agents', 'agent')
            skills = read_md_files(p / 'skills', 'skill')
            profile_manifest = read_json_file(p / 'profile.manifest.json')
            capabilities = read_json_file(p / 'capabilities.json')
            if agents or skills:
                sections[profile_name] = {
                    **meta,
                    'description': meta['stack'],
                    'profile_manifest': profile_manifest,
                    'capabilities': capabilities.get('modes', []),
                    'agents': agents,
                    'skills': skills,
                }

    # Packs
    packs_dir = root / 'packs'
    if packs_dir.exists():
        for pack_dir in sorted(packs_dir.iterdir()):
            if not pack_dir.is_dir():
                continue
            pack_name = pack_dir.name
            pack_json = pack_dir / 'pack.json'
            pack_info = {}
            if pack_json.exists():
                try:
                    pack_info = json.loads(pack_json.read_text())
                except Exception:
                    pass
            agents = read_md_files(pack_dir / 'agents', 'agent')
            skills = read_md_files(pack_dir / 'skills', 'skill')
            sections[f'pack-{pack_name}'] = {
                'label': pack_info.get('label', f'Pack: {pack_name.title()}'),
                'color': '#FF9800',
                'description': pack_info.get('description', pack_name),
                'agents': agents,
                'skills': skills,
            }

    return sections


def entry_class_for_skill(name: str) -> str:
    if name in PRIMARY_ENTRY_SKILLS:
        return 'primary task entry'
    if name in OVERLAY_ENTRY_SKILLS:
        return 'specialist overlay start'
    return 'reference or advanced'


def primary_start_for_skill_names(skill_names: list[str]) -> str:
    skill_set = set(skill_names)
    for name in PRIMARY_START_ORDER:
        if name in skill_set:
            return display_command(name)
    return '—'


def overlay_starts_for_skill_names(skill_names: list[str]) -> list[str]:
    skill_set = set(skill_names)
    return [display_command(name) for name in OVERLAY_START_SKILLS if name in skill_set]


def start_contract_for_skill_names(skill_names: list[str]) -> str:
    primary = primary_start_for_skill_names(skill_names)
    if primary == '/aikit-bootstrap-project':
        return 'Bootstrap is a no-delivery-chain start; choose a bounded overlay or repo delivery chain only after discovery.'
    return 'Choose one primary start or one bounded overlay start; overlays do not replace the default chain.'


def collect_runtime_adapters(root: Path) -> list[dict]:
    adapters = []
    for manifest in sorted((root / 'adapters').glob('*/adapter.manifest.json')):
        data = read_json_file(manifest)
        if data:
            adapters.append({
                'runtime': data.get('runtime', manifest.parent.name),
                'label': data.get('label', manifest.parent.name),
                'status': data.get('status', 'unknown'),
                'install_type': data.get('install_type', 'unknown'),
            })
    return adapters


def collect_workflow_surfaces(root: Path) -> list[dict]:
    workflows = []
    for manifest in sorted((root / 'profiles').glob('*/workflow.manifest.json')):
        data = read_json_file(manifest)
        if data:
            profile_name = data.get('profile', manifest.parent.name)
            if not is_public_profile(root, profile_name):
                continue
            recipes = data.get('recipes', [])
            workflows.append({
                'profile': profile_name,
                'default_recipe': data.get('default_recipe', 'unknown'),
                'recipe_count': len(recipes) if isinstance(recipes, list) else 0,
                'has_frontend_task_workflows': bool(data.get('frontend_task_workflows')),
            })
    return workflows


def collect_evidence_surfaces(root: Path) -> list[dict]:
    return []


def collect_product_context(root: Path) -> dict:
    return {
        'runtime_adapters': collect_runtime_adapters(root),
        'workflow_surfaces': collect_workflow_surfaces(root),
        'evidence_surfaces': collect_evidence_surfaces(root),
        'validation_commands': [
            '/aikit-doctor --check validate-product-docs',
            '/aikit-doctor --check validate-workflow-fixtures',
            '/aikit-doctor --check validate-documentation-integrity',
            '/aikit-doctor --check validate-config',
        ],
    }


# ─── HTML helpers ────────────────────────────────────────────────────────────

def h(text) -> str:
    """HTML-escape a value."""
    if isinstance(text, list):
        return html.escape(', '.join(text))
    return html.escape(str(text or ''))


def tag_badges(tags) -> str:
    if not tags:
        return ''
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(',')]
    return ''.join(f'<span class="badge">{h(t)}</span>' for t in tags)


def dep_badges(deps, color='#e53935') -> str:
    if not deps:
        return ''
    if isinstance(deps, str):
        deps = [d.strip() for d in deps.split(',')]
    return ''.join(
        f'<span class="dep-badge" style="border-color:{color}">'
        f'<span class="dep-arrow">→</span>{h(d)}</span>'
        for d in deps
    )


def ctx_badges(items, icon: str, css_class: str) -> str:
    if not items:
        return ''
    if isinstance(items, str):
        items = [i.strip() for i in items.split(',')]
    return ''.join(
        f'<span class="{css_class}">{icon} {h(i)}</span>' for i in items
    )


def render_agent_card(a: dict) -> str:
    name = a.get('name', '')
    desc = a.get('description', '')
    tags = a.get('tags', [])
    depends = a.get('depends_on', [])
    requires_mcp = a.get('requires_mcp', [])
    output_block = a.get('output_block', '')
    example = a.get('example_prompt', '')
    model = a.get('model', '')
    context_files = a.get('context_files', [])
    context_blocks = a.get('context_blocks', [])

    mcp_html = ''
    if requires_mcp:
        mcp_list = requires_mcp if isinstance(requires_mcp, list) else [requires_mcp]
        mcp_html = ''.join(
            f'<span class="mcp-badge">MCP: {h(m)}</span>' for m in mcp_list
        )

    ctx_html = (
        ctx_badges(context_files, '📄', 'ctx-file-badge') +
        ctx_badges(context_blocks, '📦', 'ctx-block-badge')
    )
    meta_html = ''.join(part for part in [tag_badges(tags), dep_badges(depends), mcp_html] if part)

    output_html = f'<span class="output-badge">→ {h(output_block)}</span>' if output_block else ''
    model_html = f'<span class="model-badge">{h(model)}</span>' if model else ''

    copy_btn = ''
    if example:
        escaped_example = example.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        copy_btn = (
            f'<button class="copy-btn" onclick="copyText(this, &quot;{escaped_example}&quot;)" '
            f'title="Скопировать промпт">📋 Копировать промпт</button>'
        )

    example_html = f'<div class="example-prompt">{h(example)}</div>' if example else ''

    return f'''
<div class="card agent-card" data-name="{h(name)}" data-desc="{h(desc)}">
  <div class="card-header">
    <span class="card-icon">🤖</span>
    <span class="card-name">{h(name)}</span>
    {model_html}
    {output_html}
  </div>
  <div class="card-desc">{h(desc)}</div>
  <div class="card-meta">{meta_html}</div>
  {f'<div class="card-meta ctx-meta">{ctx_html}</div>' if ctx_html else ''}
  {example_html}
  {copy_btn}
</div>'''


def render_skill_card(s: dict) -> str:
    name = s.get('name', '')
    desc = s.get('description', '')
    tags = s.get('tags', [])
    orchestrates = s.get('orchestrates', [])
    example = s.get('example_prompt', '')
    entry_class = entry_class_for_skill(name)
    visible_name = display_command(name)

    orch_html = dep_badges(orchestrates, color='#7B1FA2') if orchestrates else ''
    contract_badge = '<span class="contract-badge">no-delivery-chain start</span>' if name in NO_DELIVERY_START_SKILLS else ''
    entry_badges = (
        f'<span class="entry-badge entry-{entry_class.split()[0]}">{h(entry_class)}</span>'
        f'{contract_badge}'
    )

    copy_btn = ''
    if example:
        escaped_example = example.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        copy_btn = (
            f'<button class="copy-btn" onclick="copyText(this, &quot;{escaped_example}&quot;)" '
            f'title="Скопировать пример">📋 Копировать пример</button>'
        )

    example_html = f'<div class="example-prompt">{h(example)}</div>' if example else ''

    return f'''
<div class="card skill-card" data-name="{h(name)}" data-desc="{h(desc)}">
  <div class="card-header">
    <span class="card-icon">⚡</span>
    <span class="card-name">{h(visible_name)}</span>
  </div>
  <div class="card-desc">{h(desc)}</div>
  <div class="card-meta">
    {entry_badges}
    {tag_badges(tags)}
    {orch_html}
  </div>
  {example_html}
  {copy_btn}
</div>'''


def render_chain_diagram(agents: list[dict], section_color: str) -> str:
    """Render a simple visual dependency chain using flexbox."""
    if not agents:
        return ''

    # Build dependency map
    name_to_agent = {a.get('name', ''): a for a in agents}
    # Topological sort by depends_on
    visited = set()
    ordered = []

    def visit(name):
        if name in visited or name not in name_to_agent:
            return
        visited.add(name)
        a = name_to_agent[name]
        deps = a.get('depends_on', [])
        if isinstance(deps, str):
            deps = [d.strip() for d in deps.split(',') if d.strip()]
        for dep in deps:
            visit(dep)
        ordered.append(name)

    for a in agents:
        visit(a.get('name', ''))

    if len(ordered) <= 1:
        return ''

    nodes = []
    for i, name in enumerate(ordered):
        a = name_to_agent[name]
        out = a.get('output_block', '')
        out_label = f'<div class="chain-output">{h(out)}</div>' if out else ''
        arrow = '<div class="chain-arrow">→</div>' if i < len(ordered) - 1 else ''
        nodes.append(f'''
    <div class="chain-node" style="border-color:{section_color}">
      <div class="chain-name">{h(name)}</div>
      {out_label}
    </div>{arrow}''')

    return f'<div class="chain-diagram">{"".join(nodes)}</div>'


def render_section(section_id: str, section: dict) -> str:
    label = section.get('label', section_id)
    color = section.get('color', '#333')
    description = section.get('description', '')
    agents = section.get('agents', [])
    skills = section.get('skills', [])
    profile_manifest = section.get('profile_manifest', {})
    capabilities = section.get('capabilities', [])

    agent_cards = ''.join(render_agent_card(a) for a in agents)
    skill_cards = ''.join(render_skill_card(s) for s in skills)
    chain = render_chain_diagram(agents, color)
    profile_summary = ''
    if profile_manifest:
        available_skills = {skill.get('name', '') for skill in skills}

        def first_existing(*names: str) -> str:
            for name in names:
                if name in available_skills:
                    return f"/{name}"
            return "inspect-chain"

        entry_paths = {
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
        domain = profile_manifest.get('domain', '')
        taxonomy = profile_manifest.get('taxonomy', {})
        if not isinstance(taxonomy, dict):
            taxonomy = {}
        operating_class = taxonomy.get('operating_class', 'product-project')
        domain_family = taxonomy.get('domain_family', domain)
        stack_profile = taxonomy.get('stack_profile', profile_manifest.get('profile', section_id))
        core_roles = taxonomy.get('core_role_set', [])
        specialized_roles = taxonomy.get('specialized_role_set', [])
        role_aliases = taxonomy.get('role_aliases', {})
        if not isinstance(role_aliases, dict):
            role_aliases = {}
        specialized_roles = [role for role in specialized_roles if str(role) not in {'skill-builder'}]
        role_aliases = {
            role: agent_id
            for role, agent_id in role_aliases.items()
            if str(role) not in {'skill-builder'} and str(agent_id) not in {'skill-builder'}
        }
        default_chain = profile_manifest.get('default_chain', [])
        recommended_packs = profile_manifest.get('recommended_packs', [])
        recommended_skills = profile_manifest.get('recommended_skills', [])
        path_signals = profile_manifest.get('path_signals', [])
        keywords = profile_manifest.get('keywords', [])
        mode_cards = ''.join(
            f'''
<div class="mode-card">
  <div class="mode-title">{h(mode.get("name", ""))}</div>
  <div class="mode-meta">{tag_badges(mode.get("file_globs", []))}</div>
  <div class="mode-meta">{tag_badges(mode.get("suggested_skills", []))}</div>
  <div class="mode-desc">{h(", ".join(mode.get("focus", [])))}</div>
</div>'''
            for mode in capabilities
        )
        entry_path_cards = ''.join(
            f'''
<div class="mode-card">
  <div class="mode-title">{h(intent)}</div>
  <div class="mode-meta">{tag_badges([entry])}</div>
  <div class="mode-desc">{h(" → ".join(default_chain) if entry != "inspect-chain" else "Inspect the matched chain and choose the reviewer/tester path manually.")}</div>
</div>'''
            for intent, entry in entry_paths.items()
        )
        skill_names = [skill.get('name', '') for skill in skills]
        primary_start = primary_start_for_skill_names(skill_names)
        overlay_starts = ', '.join(overlay_starts_for_skill_names(skill_names)) or '—'
        start_contract = start_contract_for_skill_names(skill_names)
        profile_summary = f'''
<div class="subsection">
  <h3>Профиль</h3>
  <div class="profile-summary-card">
    <div class="profile-summary-grid">
      <div><span class="summary-label">Operating class</span><span class="summary-value">{h(operating_class)}</span></div>
      <div><span class="summary-label">Domain family</span><span class="summary-value">{h(domain_family)}</span></div>
      <div><span class="summary-label">Legacy domain</span><span class="summary-value">{h(domain)}</span></div>
      <div><span class="summary-label">Stack profile</span><span class="summary-value">{h(stack_profile)}</span></div>
      <div><span class="summary-label">Default chain</span><span class="summary-value">{h(" → ".join(default_chain))}</span></div>
      <div><span class="summary-label">Primary start</span><span class="summary-value">{h(primary_start)}</span></div>
      <div><span class="summary-label">Overlay starts</span><span class="summary-value">{h(overlay_starts)}</span></div>
      <div><span class="summary-label">Core roles</span><span class="summary-value">{h(core_roles or "—")}</span></div>
      <div><span class="summary-label">Specialized roles</span><span class="summary-value">{h(specialized_roles or "—")}</span></div>
      <div><span class="summary-label">Recommended packs</span><span class="summary-value">{h(recommended_packs or "—")}</span></div>
      <div><span class="summary-label">Recommended skills</span><span class="summary-value">{h(recommended_skills or "—")}</span></div>
      <div><span class="summary-label">Start contract</span><span class="summary-value">{h(start_contract)}</span></div>
      <div><span class="summary-label">Path signals</span><span class="summary-value">{h(path_signals or "—")}</span></div>
      <div><span class="summary-label">Keywords</span><span class="summary-value">{h(keywords or "—")}</span></div>
      <div><span class="summary-label">Capability modes</span><span class="summary-value">{h([m.get("name", "") for m in capabilities])}</span></div>
      <div><span class="summary-label">Role aliases</span><span class="summary-value">{h([f"{role}→{agent_id}" for role, agent_id in sorted(role_aliases.items())] or "—")}</span></div>
    </div>
    <div class="subsection">
      <h3>Recommended Entry Paths</h3>
      <div class="modes-grid">{entry_path_cards}</div>
    </div>
    <div class="subsection">
      <h3>Workflow Playbook</h3>
      <div class="summary-value">
        Default chain runs as: <strong>{h(" → ".join(default_chain))}</strong>.<br>
        Primary start is <strong>{h(primary_start)}</strong>. Overlay starts are <strong>{h(overlay_starts)}</strong>.<br>
        Choose one primary start or one bounded overlay start; overlays do not replace canonical delivery.
      </div>
    </div>
    {f'<div class="modes-grid">{mode_cards}</div>' if mode_cards else ''}
  </div>
</div>'''

    agents_section = ''
    if agents:
        agents_section = f'''
<div class="subsection">
  <h3>Агенты <span class="count-badge">{len(agents)}</span></h3>
  {chain}
  <div class="cards-grid">{agent_cards}</div>
</div>'''

    skills_section = ''
    if skills:
        skills_section = f'''
<div class="subsection">
  <h3>Скиллы <span class="count-badge">{len(skills)}</span></h3>
  <div class="cards-grid">{skill_cards}</div>
</div>'''

    return f'''
<div class="section" id="section-{h(section_id)}" style="display:none">
  <div class="section-header" style="border-left-color:{color}">
    <h2>{h(label)}</h2>
    <p class="section-desc">{h(description)}</p>
  </div>
  {profile_summary}
  {agents_section}
  {skills_section}
</div>'''


def render_tabs(sections: dict) -> str:
    tabs = []
    for section_id, section in sections.items():
        label = section.get('label', section_id)
        color = section.get('color', '#333')
        count = len(section.get('agents', [])) + len(section.get('skills', []))
        tabs.append(
            f'<button class="tab-btn" data-target="section-{h(section_id)}" '
            f'style="--tab-color:{color}" onclick="showSection(this)">'
            f'{h(label)} <span class="tab-count">{count}</span></button>'
        )
    return '\n'.join(tabs)


def render_product_overview(context: dict, total_agents: int, total_skills: int, section_count: int) -> str:
    runtime_cards = ''.join(
        f'''
<div class="overview-mini-card">
  <span class="summary-label">{h(adapter.get("runtime", ""))}</span>
  <span class="summary-value">{h(adapter.get("label", ""))}</span>
  <span class="badge">{h(adapter.get("status", ""))}</span>
  <span class="badge">{h(adapter.get("install_type", ""))}</span>
</div>'''
        for adapter in context.get('runtime_adapters', [])
    )
    workflow_cards = ''.join(
        f'''
<div class="overview-mini-card">
  <span class="summary-label">{h(workflow.get("profile", ""))}</span>
  <span class="summary-value">{h(workflow.get("default_recipe", ""))}</span>
  <span class="badge">{h(str(workflow.get("recipe_count", 0)) + " recipes")}</span>
  {f'<span class="badge">frontend task workflow</span>' if workflow.get("has_frontend_task_workflows") else ''}
</div>'''
        for workflow in context.get('workflow_surfaces', [])
    )
    evidence_cards = ''.join(
        f'''
<div class="overview-mini-card">
  <span class="summary-label">{h(surface.get("name", ""))}</span>
  <span class="summary-value">{h(surface.get("path", ""))}</span>
  <span class="badge">{h(str(surface.get("count", 0)) + " sources")}</span>
</div>'''
        for surface in context.get('evidence_surfaces', [])
    )
    validator_cards = ''.join(
        f'<code class="validator-chip">{h(command)}</code>'
        for command in context.get('validation_commands', [])
    )
    command_cards = ''.join(
        f'''
<div class="overview-mini-card">
  <span class="summary-label">{h(item.get("command", ""))}</span>
  <span class="badge">{h(item.get("entry", ""))}</span>
  <span class="summary-value">{h(item.get("activates", ""))}</span>
</div>'''
        for item in VISIBLE_COMMAND_OVERVIEW
    )
    return f'''
<section class="catalog-overview" aria-label="Catalog Overview">
  <div class="overview-header">
    <div>
      <p class="kicker">Catalog Overview</p>
      <h1>Profiles, runtimes, workflows, evidence and validators in one local catalog</h1>
      <p class="overview-copy">Start with Start Here, then use this page as a browse and reference surface. This private-repository compatible page is generated static HTML and does not require GitHub Pages or public hosting.</p>
    </div>
    <div class="overview-stats" aria-label="Catalog totals">
      <div><span>{h(total_agents)}</span><small>Agents</small></div>
      <div><span>{h(total_skills)}</span><small>Skills</small></div>
      <div><span>{h(section_count)}</span><small>Profiles and packs</small></div>
    </div>
  </div>
  <div class="overview-grid">
    <div class="overview-panel">
      <h2>Runtime choices</h2>
      <div class="overview-stack">{runtime_cards}</div>
    </div>
    <div class="overview-panel">
      <h2>Workflow surfaces</h2>
      <div class="overview-stack">{workflow_cards}</div>
    </div>
    <div class="overview-panel">
      <h2>Evidence surfaces</h2>
      <div class="overview-stack">{evidence_cards}</div>
    </div>
    <div class="overview-panel">
      <h2>Validation commands</h2>
      <div class="validator-list">{validator_cards}</div>
      <code class="validator-chip">/aikit-docs --refresh catalog</code>
      <a class="overview-link" href="../public/get-started.md">Return to Get Started for the project-first install and bootstrap path.</a>
    </div>
    <div class="overview-panel">
      <h2>Visible commands</h2>
      <div class="overview-stack">{command_cards}</div>
      <a class="overview-link" href="../public/start-here.md">Start with Start Here before using this catalog as a browse/reference surface.</a>
      <a class="overview-link" href="../public/profiles-summary.md">Profile-local overlays such as /setup-admin appear only after the profile is known.</a>
    </div>
  </div>
</section>'''


# ─── Full HTML template ──────────────────────────────────────────────────────

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AIKit — Каталог агентов и скиллов</title>
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #22263a;
    --border: #2d3148;
    --text: #e2e8f0;
    --text-muted: #8892a4;
    --accent: #6366f1;
    --success: #22c55e;
    --warning: #f59e0b;
    --radius: 10px;
    --shadow: 0 2px 12px rgba(0,0,0,.35);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
  }

  /* ── Header ── */
  .header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 18px 28px;
    display: flex;
    align-items: center;
    gap: 16px;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .header-logo { font-size: 24px; }
  .header-title { font-size: 18px; font-weight: 700; }
  .header-sub { font-size: 13px; color: var(--text-muted); margin-left: auto; }
  .header-links {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .header-link {
    color: var(--text-muted);
    text-decoration: none;
    font-size: 12px;
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 5px 10px;
    transition: color .15s, border-color .15s, background .15s;
  }
  .header-link:hover {
    color: var(--text);
    border-color: var(--accent);
    background: var(--surface2);
  }

  .search-wrap { position: relative; }
  .search-input {
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: var(--radius);
    padding: 7px 12px 7px 32px;
    font-size: 14px;
    width: 220px;
    transition: border-color .2s;
  }
  .search-input:focus { outline: none; border-color: var(--accent); }
  .search-icon {
    position: absolute;
    left: 9px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-muted);
    font-size: 14px;
  }

  /* ── Layout ── */
  .layout { display: flex; height: calc(100vh - 61px); }

  /* ── Sidebar tabs ── */
  .sidebar {
    width: 200px;
    min-width: 200px;
    background: var(--surface);
    border-right: 1px solid var(--border);
    overflow-y: auto;
    padding: 12px 8px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .sidebar-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: .08em;
    color: var(--text-muted);
    text-transform: uppercase;
    padding: 6px 8px 2px;
  }
  .tab-btn {
    background: transparent;
    border: none;
    color: var(--text-muted);
    text-align: left;
    padding: 9px 12px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    transition: background .15s, color .15s;
    border-left: 3px solid transparent;
  }
  .tab-btn:hover { background: var(--surface2); color: var(--text); }
  .tab-btn.active {
    background: var(--surface2);
    color: var(--text);
    border-left-color: var(--tab-color, var(--accent));
    font-weight: 600;
  }
  .tab-count {
    background: var(--surface2);
    border-radius: 20px;
    padding: 1px 7px;
    font-size: 11px;
    color: var(--text-muted);
  }
  .tab-btn.active .tab-count { background: var(--bg); }

  /* ── Main content ── */
  .main {
    flex: 1;
    overflow-y: auto;
    padding: 28px 32px;
  }

  .catalog-overview {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px;
    margin-bottom: 28px;
  }
  .overview-header {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 18px;
    align-items: start;
    margin-bottom: 18px;
  }
  .kicker {
    font-size: 11px;
    color: var(--success);
    text-transform: uppercase;
    letter-spacing: .08em;
    font-weight: 700;
    margin-bottom: 6px;
  }
  .overview-header h1 {
    font-size: 22px;
    line-height: 1.25;
    margin-bottom: 8px;
  }
  .overview-copy {
    color: var(--text-muted);
    font-size: 13px;
    line-height: 1.5;
  }
  .overview-stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(78px, 1fr));
    gap: 8px;
  }
  .overview-stats div {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px;
    min-width: 78px;
  }
  .overview-stats span {
    display: block;
    color: var(--text);
    font-weight: 800;
    font-size: 18px;
  }
  .overview-stats small {
    display: block;
    color: var(--text-muted);
    font-size: 11px;
    margin-top: 2px;
  }
  .overview-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 12px;
  }
  .overview-panel {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px;
  }
  .overview-panel h2 {
    font-size: 13px;
    margin-bottom: 12px;
  }
  .overview-stack,
  .validator-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .overview-mini-card {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    border-bottom: 1px solid rgba(255,255,255,.06);
    padding-bottom: 8px;
  }
  .overview-mini-card:last-child { border-bottom: none; padding-bottom: 0; }
  .validator-chip {
    display: block;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 7px 9px;
    color: var(--text);
    font-size: 11px;
    white-space: normal;
    line-height: 1.4;
  }
  .overview-link {
    display: inline-block;
    margin-top: 12px;
    color: #93c5fd;
    font-size: 12px;
    text-decoration: none;
  }

  .section-header {
    border-left: 4px solid #6366f1;
    padding-left: 14px;
    margin-bottom: 28px;
  }
  .section-header h2 { font-size: 22px; font-weight: 700; }
  .section-desc { font-size: 14px; color: var(--text-muted); margin-top: 4px; }

  .subsection { margin-bottom: 36px; }
  .subsection h3 {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: .06em;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .count-badge {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 1px 8px;
    font-size: 11px;
    color: var(--text-muted);
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
  }

  .profile-summary-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .profile-summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
  }
  .summary-label {
    display: block;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .06em;
    color: var(--text-muted);
    margin-bottom: 4px;
  }
  .summary-value {
    display: block;
    font-size: 13px;
    color: var(--text);
    line-height: 1.5;
  }
  .modes-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 12px;
  }
  .mode-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .mode-title {
    font-weight: 700;
    font-size: 13px;
    color: var(--text);
    font-family: 'SF Mono', monospace;
  }
  .mode-desc {
    font-size: 12px;
    color: var(--text-muted);
    line-height: 1.5;
  }

  /* ── Cards grid ── */
  .cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 14px;
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    transition: border-color .2s, transform .15s;
  }
  .card:hover { border-color: var(--accent); transform: translateY(-1px); }
  .card.hidden { display: none; }

  .card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .card-icon { font-size: 16px; flex-shrink: 0; }
  .card-name { font-weight: 700; font-size: 15px; font-family: 'SF Mono', monospace; }
  .agent-card .card-name { color: #93c5fd; }
  .skill-card .card-name { color: #86efac; }

  .card-desc { font-size: 13px; color: var(--text-muted); line-height: 1.5; }

  .card-meta { display: flex; flex-wrap: wrap; gap: 6px; }

  /* ── Badges ── */
  .badge {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 2px 9px;
    font-size: 11px;
    color: var(--text-muted);
  }
  .entry-badge {
    border-radius: 20px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 600;
  }
  .entry-primary {
    background: rgba(34, 197, 94, .12);
    border: 1px solid rgba(34, 197, 94, .35);
    color: #86efac;
  }
  .entry-specialist {
    background: rgba(96, 165, 250, .12);
    border: 1px solid rgba(96, 165, 250, .35);
    color: #93c5fd;
  }
  .entry-reference {
    background: rgba(148, 163, 184, .12);
    border: 1px solid rgba(148, 163, 184, .35);
    color: #cbd5e1;
  }
  .contract-badge {
    background: rgba(251, 191, 36, .12);
    border: 1px solid rgba(251, 191, 36, .35);
    border-radius: 20px;
    padding: 2px 9px;
    font-size: 11px;
    color: #fde68a;
  }
  .dep-badge {
    border: 1px solid #e53935;
    border-radius: 20px;
    padding: 2px 9px;
    font-size: 11px;
    color: #ef9a9a;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .dep-arrow { opacity: .6; }
  .mcp-badge {
    background: rgba(99, 102, 241, .15);
    border: 1px solid rgba(99, 102, 241, .4);
    border-radius: 20px;
    padding: 2px 9px;
    font-size: 11px;
    color: #a5b4fc;
  }
  .output-badge {
    background: rgba(34, 197, 94, .1);
    border: 1px solid rgba(34, 197, 94, .3);
    border-radius: 20px;
    padding: 2px 9px;
    font-size: 11px;
    color: #86efac;
    margin-left: auto;
  }
  .model-badge {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 2px 9px;
    font-size: 11px;
    color: var(--text-muted);
  }

  /* ── Context badges ── */
  .ctx-meta { margin-top: -4px; }
  .ctx-file-badge {
    background: rgba(34, 197, 94, .08);
    border: 1px solid rgba(34, 197, 94, .25);
    border-radius: 20px;
    padding: 2px 9px;
    font-size: 11px;
    color: #86efac;
  }
  .ctx-block-badge {
    background: rgba(251, 191, 36, .08);
    border: 1px solid rgba(251, 191, 36, .25);
    border-radius: 20px;
    padding: 2px 9px;
    font-size: 11px;
    color: #fde68a;
  }

  /* ── Example prompt ── */
  .example-prompt {
    background: var(--surface2);
    border-left: 3px solid var(--accent);
    border-radius: 0 6px 6px 0;
    padding: 8px 12px;
    font-size: 12px;
    color: var(--text-muted);
    font-style: italic;
    line-height: 1.5;
  }

  /* ── Copy button ── */
  .copy-btn {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text-muted);
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
    cursor: pointer;
    transition: background .15s, color .15s;
    align-self: flex-start;
  }
  .copy-btn:hover { background: var(--surface2); color: var(--text); }
  .copy-btn.copied { color: var(--success); border-color: var(--success); }

  /* ── Chain diagram ── */
  .chain-diagram {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 18px;
    margin-bottom: 16px;
    overflow-x: auto;
  }
  .chain-node {
    background: var(--surface);
    border: 2px solid #6366f1;
    border-radius: 8px;
    padding: 8px 14px;
    text-align: center;
    min-width: 130px;
  }
  .chain-name { font-size: 12px; font-weight: 600; font-family: 'SF Mono', monospace; color: #93c5fd; }
  .chain-output { font-size: 10px; color: #86efac; margin-top: 3px; }
  .chain-arrow { font-size: 18px; color: var(--text-muted); flex-shrink: 0; }

  /* ── Empty state ── */
  .empty-state {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-muted);
    font-size: 15px;
  }
  .empty-state-icon { font-size: 48px; margin-bottom: 12px; }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

  /* ── Toast ── */
  .toast {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: var(--surface);
    border: 1px solid var(--success);
    color: var(--success);
    padding: 10px 18px;
    border-radius: var(--radius);
    font-size: 13px;
    opacity: 0;
    transform: translateY(8px);
    transition: opacity .2s, transform .2s;
    pointer-events: none;
    z-index: 999;
  }
  .toast.show { opacity: 1; transform: translateY(0); }
</style>
</head>
<body>

<header class="header">
  <span class="header-logo">🤖</span>
  <span class="header-title">AIKit — Агенты и скиллы</span>
  <div class="search-wrap">
    <span class="search-icon">🔍</span>
    <input class="search-input" type="text" placeholder="Поиск..." oninput="filterCards(this.value)">
  </div>
  <div class="header-links">
    <a class="header-link" href="./index.html">Docs Home</a>
    <a class="header-link" href="../public/product-story.md">Product Story</a>
    <a class="header-link" href="../public/start-here.md">Start Here</a>
    <a class="header-link" href="../public/agents-skills-reference.md">Agents & Skills</a>
          <a class="header-link" href="../public/release-center.md">Release Center</a>
          <a class="header-link" href="../public/get-started.md">Get Started</a>
          <a class="header-link" href="../public/install-matrix.md">Install Matrix</a>
          <a class="header-link" href="../public/runtime-maturity-review.md">Runtime Review</a>
          <a class="header-link" href="../public/profiles-summary.md">Profiles Summary</a>
          <a class="header-link" href="../public/compatibility-matrix.md">Compatibility Matrix</a>
          <a class="header-link" href="../public/marketplace.md">Marketplace</a>
          <a class="header-link" href="../public/publishing-workflow.md">Publishing Workflow</a>
  </div>
  <span class="header-sub">Claude Code · AIKit</span>
</header>

<div class="layout">
  <nav class="sidebar">
    <div class="sidebar-label">Профили</div>
    {TABS}
  </nav>
  <main class="main" id="main">
    {OVERVIEW}
    {SECTIONS}
    <div class="empty-state" id="no-results" style="display:none">
      <div class="empty-state-icon">🔍</div>
      Ничего не найдено
    </div>
  </main>
</div>

<div class="toast" id="toast">✓ Скопировано!</div>

<script>
  let activeSection = null;

  function showSection(btn) {
    // Update tabs
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    // Show/hide sections
    const target = btn.dataset.target;
    document.querySelectorAll('.section').forEach(s => {
      s.style.display = s.id === target ? 'block' : 'none';
    });
    activeSection = target;
    // Reset search
    document.querySelector('.search-input').value = '';
    filterCards('');
  }

  function filterCards(query) {
    const q = query.toLowerCase().trim();
    let visibleCount = 0;
    const section = document.getElementById(activeSection);
    if (!section) return;
    section.querySelectorAll('.card').forEach(card => {
      const name = (card.dataset.name || '').toLowerCase();
      const desc = (card.dataset.desc || '').toLowerCase();
      const text = card.textContent.toLowerCase();
      const visible = !q || name.includes(q) || desc.includes(q) || text.includes(q);
      card.classList.toggle('hidden', !visible);
      if (visible) visibleCount++;
    });
    const noResults = document.getElementById('no-results');
    if (noResults) noResults.style.display = (q && visibleCount === 0) ? 'block' : 'none';
  }

  function copyText(btn, text) {
    navigator.clipboard.writeText(text).then(() => {
      btn.classList.add('copied');
      btn.textContent = '✓ Скопировано';
      showToast();
      setTimeout(() => {
        btn.classList.remove('copied');
        btn.textContent = '📋 Копировать ' + (btn.closest('.agent-card') ? 'промпт' : 'пример');
      }, 2000);
    }).catch(() => {
      // Fallback
      const el = document.createElement('textarea');
      el.value = text;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      showToast();
    });
  }

  function showToast() {
    const t = document.getElementById('toast');
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2000);
  }

  // Activate first tab on load
  window.addEventListener('DOMContentLoaded', () => {
    const first = document.querySelector('.tab-btn');
    if (first) first.click();
  });
</script>
</body>
</html>
'''


# ─── Main ───────────────────────────────────────────────────────────────────

def legacy_catalog_redirect_stub() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=./generated/catalog.html">
  <title>AIKit Catalog Redirect</title>
</head>
<body>
  <p>Moved to <a href="./generated/catalog.html">docs/generated/catalog.html</a>.</p>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description='Generate agents catalog HTML')
    parser.add_argument('--root', default=None,
                        help='Path to claude-config root (default: parent of scripts/)')
    parser.add_argument('--out', default=None,
                        help='Output HTML file (default: docs/generated/catalog.html)')
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    root = Path(args.root).resolve() if args.root else script_dir.parent
    out = Path(args.out).resolve() if args.out else root / 'docs' / 'generated' / 'catalog.html'

    if not root.exists():
        print(f'Error: root not found: {root}', file=sys.stderr)
        sys.exit(1)

    print(f'Root:   {root}')
    print(f'Output: {out}')

    sections = collect_data(root)

    total_agents = sum(len(s.get('agents', [])) for s in sections.values())
    total_skills = sum(len(s.get('skills', [])) for s in sections.values())
    print(f'Found:  {total_agents} agents, {total_skills} skills in {len(sections)} sections')

    tabs_html = render_tabs(sections)
    sections_html = '\n'.join(render_section(sid, sec) for sid, sec in sections.items())
    context = collect_product_context(root)
    overview_html = render_product_overview(context, total_agents, total_skills, len(sections))

    catalog = (
        HTML_TEMPLATE
        .replace('{TABS}', tabs_html)
        .replace('{OVERVIEW}', overview_html)
        .replace('{SECTIONS}', sections_html)
    )
    catalog = '\n'.join(line.rstrip() for line in catalog.splitlines()) + '\n'

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(catalog, encoding='utf-8')
    if args.out is None:
        legacy_out = root / 'docs' / 'catalog.html'
        legacy_out.write_text(legacy_catalog_redirect_stub(), encoding='utf-8')
        print(f'Updated compatibility redirect → {legacy_out}')
    print(f'Done → {out}')


if __name__ == '__main__':
    main()
