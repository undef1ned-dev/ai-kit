#!/usr/bin/env python3
"""
Build the AIKit documentation site docs/site/ from the Markdown guide and the kit sources.

Sources:
    docs/guide/*.md, docs/roadmap.md, docs/runtime-support.md  — pages (Markdown is the source of truth)
    base/, profiles/, packs/, presets/                          — the catalog page
    docs/site/assets/site.css, site.js                         — hand-written, not generated

Output: docs/site/*.html and docs/site/assets/search-index.js. The site is committed, so it opens
right after cloning; static checks run --check to make sure it matches the sources.

Markdown extensions (plain Markdown on GitHub, components on the site):
    <!-- cards -->  before a list of "[Title](link) — text" items  → a grid of link cards
    <!-- chain -->  before a list of "**name** — text" items       → a flow diagram with arrows
    <!-- steps -->  before an ordered list                         → numbered steps
    > [!NOTE] / [!TIP] / [!WARNING] / [!IMPORTANT]                  → callouts (GitHub alert syntax)

Usage:
    python3 scripts/generate-docs.py            # write docs/site/
    python3 scripts/generate-docs.py --check    # exit 1 if docs/site/ is out of date or a link is broken
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / "docs" / "site"
# Files outside the site link to GitHub: the same link works locally and on GitHub Pages
REPO_URL = "https://github.com/undef1ned-dev/ai-kit"
SEARCH_INDEX = "assets/search-index.js"
CATALOG_SLUG = "catalog"
COMMANDS_PAGE = "docs/guide/commands.md"

# (slug, source, nav label, nav group); source None — the page is generated from the kit sources
PAGES = [
    ("index", "docs/guide/index.md", "Что такое AIKit", "Начало"),
    ("glossary", "docs/guide/glossary.md", "Термины", "Начало"),
    ("getting-started", "docs/guide/getting-started.md", "Установка", "Начало"),
    ("how-it-works", "docs/guide/how-it-works.md", "Как это работает", "Как устроено"),
    ("daily-work", "docs/guide/daily-work.md", "Работа с агентами", "Как устроено"),
    ("commands", "docs/guide/commands.md", "Команды", "Как устроено"),
    (CATALOG_SLUG, None, "Каталог профилей", "Справочник"),
    ("runtime-support", "docs/runtime-support.md", "Поддержка runtime", "Справочник"),
    ("known-issues", "docs/guide/known-issues.md", "Известные ошибки", "Справочник"),
    ("roadmap", "docs/roadmap.md", "Roadmap", "Справочник"),
    ("adding-a-stack", "docs/guide/adding-a-stack.md", "Как добавить стек", "Развитие кита"),
    ("developing-aikit", "docs/guide/developing-aikit.md", "Разработка AIKit", "Развитие кита"),
]

PROFILE_ROLES = ("architect", "coder", "tester", "reviewer")
ROLE_LABELS = {"architect": "архитектор", "coder": "кодер", "tester": "тестировщик", "reviewer": "ревьюер"}
PROFILE_COLORS = {"vue-nuxt": "#00a876", "python-django": "#2f7d55", "python-fastapi": "#009688"}
DEFAULT_PROFILE_COLOR = "#64748b"
BASE_COLOR = "#4f46e5"
PACK_COLOR = "#d97706"
CALLOUTS = {"NOTE": "Заметка", "TIP": "Совет", "IMPORTANT": "Важно", "WARNING": "Внимание", "CAUTION": "Осторожно"}
PROSE_LANGS = ("", "text")
SNIPPET_LENGTH = 220
SEARCH_TEXT_LENGTH = 900

LIST_RE = re.compile(r"^(\s*)([-*]|\d+[.)])\s+(.*)$")
FENCE_RE = re.compile(r"^\s*```")
HEADING_RE = re.compile(r"^(#{1,4})\s+(.*?)\s*#*\s*$")
TABLE_SEP_RE = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
CODE_SPAN_RE = re.compile(r"(`+)(.+?)\1")
MARKER_RE = re.compile(r"^<!--\s*([\w-]+)\s*-->$")


def repo_link(path: str, is_dir: bool = False) -> str:
    return f"{REPO_URL}/{'tree' if is_dir else 'blob'}/main/{path}"


def h(text) -> str:
    return html.escape(str(text if text is not None else ""), quote=True)


def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text).lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_]+", "-", text).strip("-") or "section"


def plain(text: str) -> str:
    """Markdown line → plain text for search."""
    text = LINK_RE.sub(r"\1", text)
    text = re.sub(r"<!--.*?-->", "", text)
    text = re.sub(r"[`*>#|]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ─── Markdown → HTML ────────────────────────────────────────────────────────

class Page:
    """Render state of one page: links, headings, search sections."""

    def __init__(self, slug: str, source: str | None, slug_by_source: dict[str, str]):
        self.slug = slug
        self.source = source
        self.slug_by_source = slug_by_source
        self.title = ""
        self.toc: list[tuple[int, str, str]] = []
        self.ids: set[str] = set()
        self.sections: list[dict] = []
        self.broken_links: list[str] = []
        self.fragment_links: list[tuple[str, str, str]] = []
        self.new_section("", "")

    def new_section(self, title: str, anchor: str) -> None:
        self.sections.append({"title": title, "anchor": anchor, "text": []})

    def add_text(self, text: str) -> None:
        if text:
            self.sections[-1]["text"].append(text)

    def unique_id(self, text: str) -> str:
        base = slugify(text)
        anchor, n = base, 2
        while anchor in self.ids:
            anchor, n = f"{base}-{n}", n + 1
        self.ids.add(anchor)
        return anchor

    def resolve_link(self, url: str) -> str:
        if re.match(r"^[a-z]+:", url) or url.startswith("#"):
            return url
        path, _, fragment = url.partition("#")
        source_dir = (ROOT / self.source).parent if self.source else ROOT
        target = (source_dir / path).resolve()
        rel = target.relative_to(ROOT).as_posix() if target.is_relative_to(ROOT) else ""
        site_page = rel.removeprefix("docs/site/").removesuffix(".html")
        if rel in self.slug_by_source or (rel.startswith("docs/site/") and site_page in self.slug_by_source.values()):
            slug = self.slug_by_source.get(rel, site_page)
            if fragment:
                self.fragment_links.append((slug, fragment, f"битый якорь в {self.source}: {url}"))
            result = f"{slug}.html"
        elif target.exists():
            result = repo_link(rel, target.is_dir())
        else:
            self.broken_links.append(f"битая ссылка в {self.source}: {url}")
            return url
        return f"{result}#{fragment}" if fragment else result


def inline(text: str, page: Page) -> str:
    codes: list[str] = []

    def stash(match: re.Match) -> str:
        codes.append(f"<code>{h(match.group(2).strip())}</code>")
        return f"\x00{len(codes) - 1}\x00"

    def link(match: re.Match) -> str:
        url = html.unescape(match.group(2))
        href = page.resolve_link(url)
        external = ' target="_blank" rel="noopener"' if re.match(r"^https?:", href) else ""
        return f'<a href="{h(href)}"{external}>{match.group(1)}</a>'

    text = CODE_SPAN_RE.sub(stash, text)
    text = html.escape(text, quote=False)
    text = LINK_RE.sub(link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?![\s*])(.+?)(?<![\s*])\*(?![\w*])", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], text)


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def starts_block(line: str) -> bool:
    s = line.strip()
    return bool(
        HEADING_RE.match(line) or FENCE_RE.match(line) or LIST_RE.match(line)
        or s.startswith(">") or s.startswith("|") or s.startswith("<!--")
        or re.fullmatch(r"-{3,}|\*{3,}", s)
    )


def split_row(row: str) -> list[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|") and not row.endswith("\\|"):
        row = row[:-1]
    cells, current, in_code = [], "", False
    i = 0
    while i < len(row):
        char = row[i]
        if char == "\\" and i + 1 < len(row) and row[i + 1] == "|":
            current += "|"
            i += 2
            continue
        if char == "`":
            in_code = not in_code
        if char == "|" and not in_code:
            cells.append(current.strip())
            current = ""
        else:
            current += char
        i += 1
    cells.append(current.strip())
    return cells


def render_table(header: str, rows: list[str], page: Page) -> str:
    head = "".join(f"<th>{inline(cell, page)}</th>" for cell in split_row(header))
    body = []
    for row in rows:
        cells = split_row(row)
        page.add_text(plain(" · ".join(cells)))
        body.append("<tr>" + "".join(f"<td>{inline(cell, page)}</td>" for cell in cells) + "</tr>")
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def render_code(lines: list[str], lang: str) -> str:
    code = h("\n".join(lines))
    prose = lang in PROSE_LANGS
    label = "<span></span>" if prose else f'<span class="code-lang">{h(lang)}</span>'
    return (
        f'<div class="code-block{" wrap" if prose else ""}">'
        f'<div class="code-head">{label}<button class="copy-btn" type="button" data-copy-code>Копировать</button></div>'
        f"<pre><code>{code}</code></pre></div>"
    )


def parse_list(lines: list[str], start: int) -> tuple[list[list[str]], bool, int, int]:
    """Collect list items starting at lines[start]. Returns (item bodies, ordered, first number, next index)."""
    first = LIST_RE.match(lines[start])
    base_indent = len(first.group(1))
    ordered = first.group(2)[0].isdigit()
    number = int(re.match(r"\d+", first.group(2)).group()) if ordered else 1
    items: list[list[str]] = []
    i = start
    content_offset = 0
    while i < len(lines):
        line = lines[i]
        match = LIST_RE.match(line)
        if match and len(match.group(1)) == base_indent:
            if match.group(2)[0].isdigit() != ordered:
                break
            content_offset = base_indent + len(match.group(2)) + 1
            items.append([match.group(3)])
            i += 1
            continue
        if not line.strip():
            k = i + 1
            while k < len(lines) and not lines[k].strip():
                k += 1
            if k < len(lines) and indent_of(lines[k]) > base_indent:
                items[-1].extend([""] * (k - i))
                i = k
                continue
            next_item = LIST_RE.match(lines[k]) if k < len(lines) else None
            if next_item and len(next_item.group(1)) == base_indent and next_item.group(2)[0].isdigit() == ordered:
                i = k
                continue
            break
        if indent_of(line) > base_indent:
            items[-1].append(line[min(indent_of(line), content_offset):])
            i += 1
            continue
        if starts_block(line):
            break
        items[-1].append(line.strip())
        i += 1
    return items, ordered, number, i


def render_item(body: list[str], page: Page) -> str:
    if len(body) == 1 or all(line.strip() and not starts_block(line) for line in body):
        text = " ".join(line.strip() for line in body)
        page.add_text(plain(text))
        return inline(text, page)
    return render_blocks(body, page)


def render_cards(items: list[list[str]], page: Page) -> str:
    cards = []
    for body in items:
        text = " ".join(line.strip() for line in body)
        page.add_text(plain(text))
        match = re.match(r"^\[([^\]]+)\]\(([^)\s]+)\)\s*(?:[—–-]\s*)?(.*)$", text)
        if match:
            href = page.resolve_link(match.group(2))
            cards.append(
                f'<a class="link-card" href="{h(href)}"><span class="link-card-title">{inline(match.group(1), page)}</span>'
                f'<span class="link-card-text">{inline(match.group(3), page)}</span></a>'
            )
            continue
        match = re.match(r"^\*\*(.+?)\*\*\s*(?:[—–-]\s*)?(.*)$", text)
        title, rest = (match.group(1), match.group(2)) if match else (text, "")
        cards.append(
            f'<div class="link-card static"><span class="link-card-title">{inline(title, page)}</span>'
            f'<span class="link-card-text">{inline(rest, page)}</span></div>'
        )
    return f'<div class="card-grid">{"".join(cards)}</div>'


def render_chain(items: list[list[str]], page: Page) -> str:
    nodes = []
    for body in items:
        text = " ".join(line.strip() for line in body)
        page.add_text(plain(text))
        match = re.match(r"^\*\*(.+?)\*\*\s*(?:[—–-]\s*)?(.*)$", text)
        title, rest = (match.group(1), match.group(2)) if match else (text, "")
        nodes.append(
            f'<div class="flow-node"><span class="flow-title">{inline(title, page)}</span>'
            f'<span class="flow-text">{inline(rest, page)}</span></div>'
        )
    return '<div class="flow">' + '<span class="flow-arrow" aria-hidden="true">→</span>'.join(nodes) + "</div>"


def render_list(items: list[list[str]], ordered: bool, number: int, page: Page, component: str | None) -> str:
    if component == "cards":
        return render_cards(items, page)
    if component == "chain":
        return render_chain(items, page)
    tag = "ol" if ordered else "ul"
    css = ' class="steps"' if component == "steps" else ""
    start = f' start="{number}"' if ordered and number != 1 else ""
    body = "".join(f"<li>{render_item(item, page)}</li>" for item in items)
    return f"<{tag}{css}{start}>{body}</{tag}>"


def render_quote(lines: list[str], page: Page) -> str:
    match = re.match(r"^\[!(\w+)\]\s*$", lines[0].strip()) if lines else None
    if match and match.group(1).upper() in CALLOUTS:
        kind = match.group(1).upper()
        inner = render_blocks(lines[1:], page)
        return (
            f'<div class="callout callout-{kind.lower()}"><div class="callout-title">{CALLOUTS[kind]}</div>'
            f"{inner}</div>"
        )
    return f"<blockquote>{render_blocks(lines, page)}</blockquote>"


def render_heading(level: int, text: str, page: Page) -> str:
    content = inline(text, page)
    if level == 1:
        page.title = page.title or plain(text)
        return f'<h1 class="page-title">{content}</h1>'
    anchor = page.unique_id(plain(text))
    if level in (2, 3):
        page.toc.append((level, anchor, content))
        page.new_section(plain(text), anchor)
    else:
        page.add_text(plain(text))
    return f'<h{level} id="{anchor}"><a class="anchor" href="#{anchor}" aria-hidden="true">#</a>{content}</h{level}>'


def render_blocks(lines: list[str], page: Page) -> str:
    out: list[str] = []
    component: str | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("<!--"):
            marker = MARKER_RE.match(stripped)
            component = marker.group(1) if marker else None
            while "-->" not in lines[i]:
                i += 1
            i += 1
            continue
        if FENCE_RE.match(line):
            lang = stripped[3:].strip()
            i += 1
            code: list[str] = []
            while i < len(lines) and not FENCE_RE.match(lines[i]):
                code.append(lines[i])
                i += 1
            page.add_text(" ".join(code))
            out.append(render_code(code, lang))
            i += 1
            continue
        heading = HEADING_RE.match(line)
        if heading:
            out.append(render_heading(len(heading.group(1)), heading.group(2), page))
            i += 1
            continue
        if re.fullmatch(r"-{3,}|\*{3,}", stripped):
            out.append("<hr>")
            i += 1
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and TABLE_SEP_RE.match(lines[i + 1].strip()):
            rows: list[str] = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(lines[j])
                j += 1
            out.append(render_table(line, rows, page))
            i = j
            continue
        if stripped.startswith(">"):
            quote: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append(render_quote(quote, page))
            continue
        if LIST_RE.match(line):
            items, ordered, number, i = parse_list(lines, i)
            out.append(render_list(items, ordered, number, page, component))
            component = None
            continue
        paragraph = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not starts_block(lines[i]):
            paragraph.append(lines[i].strip())
            i += 1
        text = " ".join(paragraph)
        page.add_text(plain(text))
        out.append(f"<p>{inline(text, page)}</p>")
    return "\n".join(out)


# ─── Kit sources → catalog ──────────────────────────────────────────────────

def parse_frontmatter(text: str) -> dict:
    """YAML-like frontmatter of an agent or skill (flat keys, strings and inline lists)."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    result = {}
    for line in match.group(1).splitlines():
        kv = re.match(r"^(\w[\w-]*):\s*(.*)", line.rstrip())
        if not kv:
            continue
        key, value = kv.group(1), kv.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif value.startswith("[") and value.endswith("]"):
            value = [item.strip().strip("\"'") for item in value[1:-1].split(",") if item.strip()]
        result[key] = value
    return result


def read_entries(directory: Path, kind: str) -> list[dict]:
    """Agents (<name>.md) or skills (<name>/SKILL.md) of one layer."""
    pattern = "*/SKILL.md" if kind == "skill" else "*.md"
    entries = []
    for path in sorted(directory.glob(pattern)) if directory.exists() else []:
        data = parse_frontmatter(path.read_text(encoding="utf-8"))
        data.setdefault("name", path.parent.name if kind == "skill" else path.stem)
        data["_kind"] = kind
        data["_file"] = path.resolve().relative_to(ROOT).as_posix()
        entries.append(data)
    return entries


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def collect_data(root: Path) -> dict:
    """Catalog sections: base, every profile, every pack — with their agents and skills."""
    sections = {
        "base": {
            "kind": "base",
            "label": "Base",
            "color": BASE_COLOR,
            "description": "Ядро кита: ставится в любой проект вместе с любым профилем",
            "agents": read_entries(root / "base" / "agents", "agent"),
            "skills": read_entries(root / "base" / "skills", "skill"),
        }
    }
    for profile_dir in sorted(p for p in (root / "profiles").iterdir() if p.is_dir()):
        manifest = read_json(profile_dir / "profile.manifest.json")
        sections[profile_dir.name] = {
            "kind": "profile",
            "label": manifest.get("label", profile_dir.name),
            "color": PROFILE_COLORS.get(profile_dir.name, DEFAULT_PROFILE_COLOR),
            "description": manifest.get("stack", ""),
            "manifest": manifest,
            "agents": read_entries(profile_dir / "agents", "agent"),
            "skills": read_entries(profile_dir / "skills", "skill"),
        }
    for pack_dir in sorted(p for p in (root / "packs").iterdir() if p.is_dir()):
        info = read_json(pack_dir / "pack.json")
        sections[f"pack-{pack_dir.name}"] = {
            "kind": "pack",
            "label": info.get("label", f"Pack: {pack_dir.name}"),
            "color": PACK_COLOR,
            "description": info.get("description", ""),
            "pack": info,
            "agents": read_entries(pack_dir / "agents", "agent"),
            "skills": read_entries(pack_dir / "skills", "skill"),
        }
    return sections


def collect_presets(root: Path) -> list[dict]:
    return [read_json(path) for path in sorted((root / "presets").glob("*.json"))]


def chips(items, css: str = "chip") -> str:
    return "".join(f'<span class="{css}">{h(item)}</span>' for item in items if item)


def copy_button(text: str, label: str = "Копировать") -> str:
    return f'<button class="copy-btn" type="button" data-copy="{h(text)}">{label}</button>'


def render_entry_card(entry: dict, section_id: str) -> str:
    kind = entry["_kind"]
    name = entry.get("name", "")
    title = f"/{name}" if kind == "skill" else name
    badges = []
    if entry.get("output_block"):
        badges.append(f'<span class="chip chip-out">→ {h(entry["output_block"])}</span>')
    if str(entry.get("disable-model-invocation", "")).lower() == "true":
        badges.append('<span class="chip chip-warn">только явный вызов</span>')
    if entry.get("model"):
        badges.append(f'<span class="chip">{h(entry["model"])}</span>')
    example = entry.get("example_prompt", "")
    example_html = (
        f'<div class="entry-example"><span>{h(example)}</span>{copy_button(example)}</div>' if example else ""
    )
    return f'''<article class="entry-card entry-{kind}" id="{kind}-{h(name)}" data-filter="{h((name + " " + entry.get("description", "")).lower())}">
  <header><span class="entry-icon" aria-hidden="true">{"⚡" if kind == "skill" else "🤖"}</span><span class="entry-name">{h(title)}</span></header>
  <p>{h(entry.get("description", ""))}</p>
  {f'<div class="chips">{"".join(badges)}</div>' if badges else ""}
  {example_html}
  <a class="entry-source" href="{h(repo_link(entry["_file"]))}">{h(entry["_file"])}</a>
</article>'''


def render_contract(manifest: dict) -> str:
    agents = manifest.get("agents", {})
    flow_nodes = [
        f'<div class="flow-node"><span class="flow-title">{h(agents.get(role, "?"))}</span><span class="flow-text">{ROLE_LABELS[role]}</span></div>'
        for role in PROFILE_ROLES
    ]
    arrow = '<span class="flow-arrow" aria-hidden="true">→</span>'
    flow = (
        f'<div class="flow">{flow_nodes[0]}{arrow}{flow_nodes[1]}{arrow}'
        f'<div class="flow-parallel">{flow_nodes[2]}{flow_nodes[3]}</div></div>'
    )
    commands = "".join(
        f"<tr><td><code>{h(name)}</code></td><td><code>{h(command)}</code></td></tr>"
        for name, command in manifest.get("commands", {}).items()
    )
    specialists = "".join(
        f'<div class="mini-card"><strong>{h(spec.get("agent", ""))}</strong><span>{h(spec.get("when", ""))}</span></div>'
        for spec in manifest.get("specialists", {}).values()
    )
    pipelines = "".join(
        f'<div class="mini-card"><strong>{h(name)}</strong><span class="mono">{h(" → ".join(p.get("steps", [])))}</span><span>{h(p.get("when", ""))}</span></div>'
        for name, p in manifest.get("pipelines", {}).items()
    )
    return f'''<div class="contract">
  <h3>Цепочка агентов</h3>
  {flow}
  <div class="contract-grid">
    <div><span class="label">Роль в системе</span><span>{h(manifest.get("role", "—"))}</span></div>
    <div><span class="label">Стек</span><span>{h(manifest.get("stack", "—"))}</span></div>
    <div><span class="label">Маркеры папки (root_markers)</span><span>{chips(manifest.get("root_markers", []), "chip mono")}</span></div>
    <div><span class="label">Пути профиля (path_signals)</span><span>{chips(manifest.get("path_signals", []), "chip mono")}</span></div>
  </div>
  <h3>Команды проекта</h3>
  <div class="table-wrap"><table><thead><tr><th>Команда</th><th>По умолчанию</th></tr></thead><tbody>{commands}</tbody></table></div>
  {f'<h3>Специалисты</h3><div class="mini-grid">{specialists}</div>' if specialists else ""}
  {f'<h3>Пайплайны</h3><div class="mini-grid">{pipelines}</div>' if pipelines else ""}
</div>'''


def render_section(section_id: str, section: dict) -> str:
    agents = "".join(render_entry_card(entry, section_id) for entry in section["agents"])
    skills = "".join(render_entry_card(entry, section_id) for entry in section["skills"])
    extra = ""
    if section["kind"] == "profile":
        extra = render_contract(section["manifest"])
    elif section["kind"] == "pack":
        compatible = section["pack"].get("compatible_profiles")
        extra = (
            f'<p class="muted">Подходит к профилям: {chips(compatible)}</p>' if compatible
            else '<p class="muted">Подходит к любому профилю.</p>'
        )
    return f'''<section class="catalog-panel" id="{h(section_id)}" data-panel style="--accent-local:{section["color"]}">
  <div class="panel-head"><h2>{h(section["label"])}</h2><p>{h(section["description"])}</p></div>
  {extra}
  {f'<h3>Агенты <span class="count">{len(section["agents"])}</span></h3><div class="entry-grid">{agents}</div>' if agents else ""}
  {f'<h3>Скиллы <span class="count">{len(section["skills"])}</span></h3><div class="entry-grid">{skills}</div>' if skills else ""}
</section>'''


def render_catalog(page: Page) -> str:
    sections = collect_data(ROOT)
    presets = collect_presets(ROOT)
    page.title = "Каталог профилей"
    total_agents = sum(len(s["agents"]) for s in sections.values())
    total_skills = sum(len(s["skills"]) for s in sections.values())
    profiles = sum(1 for s in sections.values() if s["kind"] == "profile")
    packs = sum(1 for s in sections.values() if s["kind"] == "pack")

    page.new_section("Пресеты", "presets")
    preset_cards = []
    for preset in presets:
        command = f"bash .aikit-config/scripts/attach.sh --preset {preset.get('name', '')}"
        page.add_text(f"{preset.get('name')} {preset.get('label')} {preset.get('description')}")
        preset_cards.append(f'''<div class="preset-card" id="preset-{h(preset.get("name", ""))}">
  <div class="preset-name">{h(preset.get("label", ""))} <code>{h(preset.get("name", ""))}</code></div>
  <p>{h(preset.get("description", ""))}</p>
  <div class="chips">{chips(preset.get("profiles", []), "chip chip-profile")}{chips(preset.get("packs", []), "chip chip-pack")}</div>
  <div class="entry-example"><code>{h(command)}</code>{copy_button(command)}</div>
</div>''')

    tabs = "".join(
        f'<button class="tab" type="button" data-tab="{h(sid)}" style="--accent-local:{s["color"]}">{h(s["label"])}'
        f'<span class="count">{len(s["agents"]) + len(s["skills"])}</span></button>'
        for sid, s in sections.items()
    )
    panels = "\n".join(render_section(sid, s) for sid, s in sections.items())

    for sid, section in sections.items():
        page.sections.append({"title": section["label"], "anchor": sid, "text": [section["description"]]})
        for entry in section["agents"] + section["skills"]:
            prefix = "/" if entry["_kind"] == "skill" else ""
            page.sections.append({
                "title": f"{prefix}{entry['name']}",
                "anchor": f"{entry['_kind']}-{entry['name']}",
                "text": [entry.get("description", ""), section["label"]],
                "kind": "Скилл" if entry["_kind"] == "skill" else "Агент",
            })

    return f'''<h1 class="page-title">Каталог профилей</h1>
<p class="lead">Всё, что есть в ките: ядро (base), профили стеков, паки и пресеты. Страница собирается из исходников кита — описание каждого агента и скилла взято из его файла.</p>
<div class="stats">
  <div><b>{total_agents}</b><span>агенты</span></div>
  <div><b>{total_skills}</b><span>скиллы</span></div>
  <div><b>{profiles}</b><span>профили</span></div>
  <div><b>{packs}</b><span>паки</span></div>
</div>
<p>Термины — на странице <a href="glossary.html">Термины</a>, как подключить — в <a href="getting-started.html">Установке</a>.</p>
<h2 id="presets"><a class="anchor" href="#presets" aria-hidden="true">#</a>Пресеты</h2>
<p>Пресет — готовая комбинация профилей и паков. Его ставят одной командой.</p>
<div class="preset-grid">{"".join(preset_cards)}</div>
<h2 id="catalog-sections"><a class="anchor" href="#catalog-sections" aria-hidden="true">#</a>Ядро, профили и паки</h2>
<div class="catalog-tools">
  <div class="tabs" role="tablist">{tabs}</div>
  <input class="filter-input" type="search" placeholder="Фильтр по агентам и скиллам…" data-catalog-filter aria-label="Фильтр каталога">
</div>
<p class="muted filter-empty" hidden>Ничего не найдено в этом разделе.</p>
{panels}'''


# ─── Page shell ─────────────────────────────────────────────────────────────

def render_nav(current: str) -> str:
    groups: dict[str, list[str]] = {}
    for slug, _source, label, group in PAGES:
        active = ' class="active" aria-current="page"' if slug == current else ""
        groups.setdefault(group, []).append(f'<li><a href="{slug}.html"{active}>{h(label)}</a></li>')
    return "".join(
        f'<div class="nav-group"><div class="nav-title">{h(group)}</div><ul>{"".join(items)}</ul></div>'
        for group, items in groups.items()
    )


def render_toc(page: Page) -> str:
    if len(page.toc) < 2:
        return ""
    items = "".join(
        f'<li class="toc-l{level}"><a href="#{anchor}">{re.sub(r"<[^>]+>", "", content)}</a></li>'
        for level, anchor, content in page.toc
    )
    return f'<div class="toc-title">На этой странице</div><ul>{items}</ul>'


def render_pager(index: int) -> str:
    links = []
    if index > 0:
        slug, _s, label, _g = PAGES[index - 1]
        links.append(f'<a class="pager-prev" href="{slug}.html"><span>Назад</span>{h(label)}</a>')
    else:
        links.append("<span></span>")
    if index < len(PAGES) - 1:
        slug, _s, label, _g = PAGES[index + 1]
        links.append(f'<a class="pager-next" href="{slug}.html"><span>Дальше</span>{h(label)}</a>')
    return f'<nav class="pager">{"".join(links)}</nav>'


SHELL = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE} — AIKit</title>
<link rel="stylesheet" href="assets/site.css">
<script>try{var t=localStorage.getItem("aikit-theme");if(t)document.documentElement.dataset.theme=t}catch(e){}</script>
</head>
<body data-page="{SLUG}">
<header class="topbar">
  <button class="icon-btn nav-toggle" type="button" aria-label="Меню" data-nav-toggle>☰</button>
  <a class="brand" href="index.html"><span class="brand-mark">AI</span>Kit<span class="version">v{VERSION}</span></a>
  <div class="search">
    <input class="search-input" type="search" placeholder="Поиск по документации" aria-label="Поиск" autocomplete="off" data-search>
    <kbd class="search-key">/</kbd>
    <div class="search-results" hidden data-search-results></div>
  </div>
  <button class="icon-btn" type="button" aria-label="Сменить тему" data-theme-toggle>◐</button>
</header>
<div class="layout">
  <nav class="sidebar" aria-label="Разделы">{NAV}</nav>
  <main class="content">
    <article class="doc{DOC_CLASS}">
{BODY}
    </article>
    {PAGER}
    <footer class="page-footer">{SOURCE}</footer>
  </main>
  <aside class="toc" aria-label="Содержание">{TOC}</aside>
</div>
<div class="toast" role="status" data-toast>Скопировано</div>
<script src="assets/search-index.js"></script>
<script src="assets/site.js"></script>
</body>
</html>
"""


def undocumented_skills() -> list[str]:
    """Every skill of the kit is listed on the commands page."""
    text = (ROOT / COMMANDS_PAGE).read_text(encoding="utf-8")
    names = {path.parent.name for pattern in ("*/skills/*/SKILL.md", "*/*/skills/*/SKILL.md") for path in ROOT.glob(pattern)}
    return [f"скилл {name} не описан в {COMMANDS_PAGE}" for name in sorted(names) if not re.search(rf"[`/]{re.escape(name)}(?![\w-])", text)]


def build() -> tuple[dict[str, str], list[str]]:
    """Render every page. Returns ({path relative to docs/site: content}, broken links)."""
    slug_by_source = {source or f"docs/site/{slug}.html": slug for slug, source, _l, _g in PAGES}
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else ""
    outputs: dict[str, str] = {}
    search: list[dict] = []
    broken: list[str] = undocumented_skills()
    fragment_links: list[tuple[str, str, str]] = []
    ids_by_slug: dict[str, set[str]] = {}

    for index, (slug, source, label, _group) in enumerate(PAGES):
        page = Page(slug, source, slug_by_source)
        if source:
            text = (ROOT / source).read_text(encoding="utf-8").replace("\r\n", "\n")
            body = render_blocks(text.split("\n"), page)
            footer = (
                f'Исходник страницы: <a href="{h(repo_link(source))}">{h(source)}</a>'
                " — правь его, затем <code>python3 scripts/generate-docs.py</code>"
            )
        else:
            body = render_catalog(page)
            footer = "Страница собрана из <code>base/</code>, <code>profiles/</code>, <code>packs/</code> и <code>presets/</code>"
        broken += page.broken_links
        fragment_links += page.fragment_links
        ids_by_slug[slug] = page.ids | {section["anchor"] for section in page.sections}
        outputs[f"{slug}.html"] = (
            SHELL.replace("{TITLE}", h(label))
            .replace("{SLUG}", slug)
            .replace("{VERSION}", h(version))
            .replace("{NAV}", render_nav(slug))
            .replace("{DOC_CLASS}", " catalog" if slug == CATALOG_SLUG else "")
            .replace("{BODY}", body)
            .replace("{PAGER}", render_pager(index))
            .replace("{SOURCE}", footer)
            .replace("{TOC}", render_toc(page))
        )
        for section in page.sections:
            text = " ".join(section["text"]).strip()
            if not section["title"] and not text:
                continue
            search.append({
                "p": label,
                "u": f"{slug}.html" + (f"#{section['anchor']}" if section["anchor"] else ""),
                "t": section["title"] or page.title or label,
                "k": section.get("kind", ""),
                "x": text[:SEARCH_TEXT_LENGTH],
            })

    broken += [where for slug, fragment, where in fragment_links if fragment not in ids_by_slug.get(slug, set())]
    outputs[SEARCH_INDEX] = (
        "// Generated by scripts/generate-docs.py — do not edit\n"
        f"window.AIKIT_SEARCH = {json.dumps(search, ensure_ascii=False, separators=(',', ':'))};\n"
        f"window.AIKIT_SNIPPET = {SNIPPET_LENGTH};\n"
    )
    outputs = {path: "\n".join(line.rstrip() for line in content.splitlines()) + "\n" for path, content in outputs.items()}
    return outputs, broken


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the AIKit documentation site docs/site/")
    parser.add_argument("--check", action="store_true", help="do not write; exit 1 if docs/site/ is out of date")
    args = parser.parse_args()

    outputs, broken = build()
    for problem in broken:
        print(f"  ✗ {problem}")

    if args.check:
        stale = [
            path for path, content in outputs.items()
            if not (SITE_DIR / path).exists()
            or (SITE_DIR / path).read_text(encoding="utf-8").replace("\r\n", "\n") != content
        ]
        stale += sorted(
            path.name for path in SITE_DIR.glob("*.html") if path.name not in outputs
        )
        for path in stale:
            print(f"  ✗ docs/site/{path} устарел — запусти python3 scripts/generate-docs.py и закоммить результат")
        return 1 if stale or broken else 0

    for path in SITE_DIR.glob("*.html"):
        if path.name not in outputs:
            path.unlink()
    for path, content in outputs.items():
        target = SITE_DIR / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    print(f"docs/site/: {len(outputs) - 1} страниц, индекс поиска — {SEARCH_INDEX}")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
