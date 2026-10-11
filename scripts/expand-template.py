#!/usr/bin/env python3
"""
Expand a skill template: reads a profile skill config (.md with tvar_* frontmatter
and optional [BLOCK_NAME] body sections), substitutes into the named template.

Usage:
    python scripts/expand-template.py <skill.md> <templates-dir>

Expands skill.md in-place when it contains a `template:` frontmatter field.
If no `template:` field found — file is left unchanged.

Template syntax:
  {{VAR}}        — replaced with tvar_VAR from frontmatter (inline, no newline added)
  {{BLOCK}}      — replaced with [BLOCK] section from file body:
                   • non-empty → value + trailing newline
                   • empty     → empty string (no newline)

Profile file format:
  ---
  name: "implement-feature"
  template: "implement-feature"          ← template name (without .md.tmpl)
  profile: "python-fastapi"
  tvar_PLATFORM: FastAPI                 ← single-line variables
  tvar_PREFIX: fastapi
  tvar_TESTER_DESC: "async pytest ..."
  tvar_TAGS: '"fastapi", "python"'       ← inline list items (no brackets)
  tvar_ORCHESTRATES: '"a", "b", "c"'
  tvar_EXAMPLE_PROMPT: "..."
  ---

  [STEP1_CONTEXT]                        ← optional multi-line blocks
  - Прочитай main.py, models/, routers/
  - Выведи ARCHITECT_PLAN

  [PLATFORM_STEP]
  ## Шаг 4 — Миграция
  ...
"""

import re
import sys
from pathlib import Path


# ─── Frontmatter ─────────────────────────────────────────────────────────────

def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (raw_frontmatter_yaml, body). Body may be empty."""
    m = re.match(r'^---[ \t]*\r?\n(.*?\r?\n)---[ \t]*\r?\n?', text, re.DOTALL)
    if not m:
        return '', text
    return m.group(1), text[m.end():]


def parse_frontmatter(yaml_text: str) -> dict:
    """Minimal YAML parser: handles string, quoted string. No nesting."""
    result = {}
    for line in yaml_text.splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith('#'):
            continue
        kv = re.match(r'^([\w][\w-]*):\s*(.*)', line)
        if not kv:
            continue
        key, val = kv.group(1), kv.group(2).strip()
        # Strip surrounding quotes (single or double)
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
            val = val[1:-1]
        result[key] = val
    return result


# ─── Body block parser ────────────────────────────────────────────────────────

def parse_body_blocks(body: str) -> dict[str, str]:
    """
    Parse [BLOCK_NAME]\\ncontent sections from the file body.
    Block names: uppercase ASCII + digits + underscores.
    Content is everything until the next [BLOCK_NAME] or end of file.
    """
    blocks: dict[str, str] = {}
    current_key: str | None = None
    buf: list[str] = []

    for line in body.splitlines():
        m = re.match(r'^\[([A-Z][A-Z0-9_]*)\]\s*$', line)
        if m:
            if current_key is not None:
                blocks[current_key] = '\n'.join(buf).strip()
            current_key = m.group(1)
            buf = []
        else:
            buf.append(line)

    if current_key is not None:
        blocks[current_key] = '\n'.join(buf).strip()

    return blocks


# ─── Template expansion ───────────────────────────────────────────────────────

def expand(template_text: str, inline_vars: dict[str, str], blocks: dict[str, str]) -> str:
    """
    Replace {{VAR}} markers in template_text.
    - inline_vars: simple single-line replacements
    - blocks: multi-line replacements
      • non-empty value  → value + '\\n'  (ensures newline after block)
      • empty / missing  → ''             (removes the placeholder line)
    """
    result = template_text

    # Inline variables first (faster, no newline logic needed)
    for key, val in inline_vars.items():
        result = result.replace('{{' + key + '}}', val)

    # Block variables: replace `{{BLOCK}}\n` or `{{BLOCK}}` (end of file)
    # Preserve empty-block lines only if followed by non-block text
    def block_replacer(m: re.Match) -> str:
        key = m.group(1)
        val = blocks.get(key, '').strip()
        if val:
            return val + '\n'   # content + single newline; template provides separators
        return ''               # empty block: remove placeholder + its newline

    result = re.sub(r'\{\{([A-Z][A-Z0-9_]*)\}\}\n?', block_replacer, result)

    # Collapse 3+ consecutive newlines to 2 (one blank line) for clean output
    result = re.sub(r'\n{3,}', '\n\n', result)

    return result


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 3:
        print(f'Usage: {sys.argv[0]} <skill.md> <templates-dir>', file=sys.stderr)
        sys.exit(1)

    skill_path = Path(sys.argv[1])
    templates_dir = Path(sys.argv[2])

    if not skill_path.exists():
        print(f'Error: file not found: {skill_path}', file=sys.stderr)
        sys.exit(1)

    text = skill_path.read_text(encoding='utf-8')
    fm_yaml, body = split_frontmatter(text)

    if not fm_yaml:
        # No frontmatter — nothing to do
        return

    fm = parse_frontmatter(fm_yaml)
    template_name = fm.get('template', '').strip()

    if not template_name:
        # Not a template-based skill
        return

    tmpl_path = templates_dir / f'{template_name}.md.tmpl'
    if not tmpl_path.exists():
        print(f'Warning: template not found: {tmpl_path}', file=sys.stderr)
        return

    template_text = tmpl_path.read_text(encoding='utf-8')

    # Collect inline vars from tvar_* frontmatter fields
    inline_vars: dict[str, str] = {}
    for k, v in fm.items():
        if k.startswith('tvar_'):
            var_name = k[5:]   # strip "tvar_" prefix
            inline_vars[var_name] = v

    # Map standard frontmatter fields as well
    inline_vars.setdefault('PROFILE', fm.get('profile', ''))
    inline_vars.setdefault('EXAMPLE_PROMPT', fm.get('example_prompt', ''))

    # Parse multi-line block sections from body
    blocks = parse_body_blocks(body)

    # Expand template
    expanded = expand(template_text, inline_vars, blocks)

    # Write back in-place
    skill_path.write_text(expanded, encoding='utf-8')
    print(f'  expanded: {skill_path.name}')


if __name__ == '__main__':
    main()
