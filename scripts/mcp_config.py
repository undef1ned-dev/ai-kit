#!/usr/bin/env python3
"""
Install AIKit MCP servers into a project in the native format of each runtime.

Source of truth: mcp.json in base/, profiles/<profile>/ and packs/<pack>/:

    {
      "servers": {
        "<name>": {"command": "npx", "args": ["-y", "pkg@1.2.3"], "env_vars": ["TOKEN"]},  # stdio
        "<name>": {"url": "https://example.com/mcp"}                                      # remote HTTP, OAuth
      }
    }

env_vars lists variables passed from the user's environment by name: values never live in configs.

Targets:
    claude   — .mcp.json ("mcpServers")
    codex    — .codex/config.toml ([mcp_servers.<name>] in an AIKit-managed block)
    opencode — opencode.json ("mcp")

Servers installed by the previous run are tracked in .aikit/mcp-servers.json and replaced;
servers the user added themselves are kept.

Usage:
    python3 scripts/mcp_config.py <claude|codex|opencode> --profiles a+b [--packs "x y"] [--workspace .]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = Path(".aikit") / "mcp-servers.json"
CODEX_BLOCK_BEGIN = "# BEGIN AIKIT MCP — managed by AIKit installer, edits inside this block are overwritten"
CODEX_BLOCK_END = "# END AIKIT MCP"
OPENCODE_SCHEMA = "https://opencode.ai/config.json"
RUNTIMES = ("claude", "codex", "opencode")


def collect_servers(profiles: list[str], packs: list[str]) -> dict[str, dict]:
    sources = [ROOT / "base", *(ROOT / "profiles" / name for name in profiles), *(ROOT / "packs" / name for name in packs)]
    servers: dict[str, dict] = {}
    for source in sources:
        config_path = source / "mcp.json"
        if config_path.exists():
            servers.update(json.loads(config_path.read_text(encoding="utf-8")).get("servers", {}))
    for name, server in servers.items():
        if ("command" in server) == ("url" in server):
            raise SystemExit(f"MCP server '{name}': exactly one of 'command' or 'url' is required")
    return servers


def render_claude(server: dict) -> dict:
    if "url" in server:
        return {"type": "http", "url": server["url"]}
    rendered = {"command": server["command"], "args": server.get("args", [])}
    if server.get("env_vars"):
        rendered["env"] = {var: "${" + var + "}" for var in server["env_vars"]}
    return rendered


def render_opencode(server: dict) -> dict:
    if "url" in server:
        return {"type": "remote", "url": server["url"]}
    rendered = {"type": "local", "command": [server["command"], *server.get("args", [])]}
    if server.get("env_vars"):
        rendered["environment"] = {var: "{env:" + var + "}" for var in server["env_vars"]}
    return rendered


def toml_value(value) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    return json.dumps(value, ensure_ascii=False)


def render_codex_block(servers: dict[str, dict]) -> str:
    tables = []
    for name, server in servers.items():
        lines = [f"[mcp_servers.{name}]"]
        if "url" in server:
            lines.append(f"url = {toml_value(server['url'])}")
        else:
            lines.append(f"command = {toml_value(server['command'])}")
            lines.append(f"args = {toml_value(server.get('args', []))}")
            if server.get("env_vars"):
                lines.append(f"env_vars = {toml_value(server['env_vars'])}")
        tables.append("\n".join(lines))
    return "\n".join([CODEX_BLOCK_BEGIN, "\n\n".join(tables), CODEX_BLOCK_END]) + "\n"


def read_state(workspace: Path) -> dict:
    path = workspace / STATE_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_state(workspace: Path, runtime: str, names: list[str]) -> None:
    state = read_state(workspace)
    state[runtime] = names
    path = workspace / STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def merge_json_servers(path: Path, key: str, rendered: dict[str, dict], previous: list[str], skeleton: dict) -> list[str]:
    """Replace servers from the previous AIKit run inside a JSON config; user servers stay. Returns installed names."""
    if path.exists():
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"! {path.name} не разобран как JSON (комментарии?) — MCP-серверы не добавлены", file=sys.stderr)
            return previous
    else:
        config = dict(skeleton)
    section = config.setdefault(key, {})
    for name in previous:
        section.pop(name, None)
    installed = []
    for name, server in rendered.items():
        if name in section:
            print(f"! MCP-сервер '{name}' уже настроен в {path.name} — оставлен как есть", file=sys.stderr)
            continue
        section[name] = server
        installed.append(name)
    if not section:
        config.pop(key)
    write_json(path, config)
    return installed


def strip_codex_blocks(text: str) -> str:
    # The second pattern is the agents block written by AIKit versions before 2.0
    for begin, end in ((CODEX_BLOCK_BEGIN, CODEX_BLOCK_END), ("# BEGIN AIKIT GENERATED", "# END AIKIT GENERATED")):
        text = re.sub(rf"{re.escape(begin)}.*?{re.escape(end)}\n?", "", text, flags=re.DOTALL)
    return text.strip()


def merge_codex(workspace: Path, servers: dict[str, dict]) -> list[str]:
    config_path = workspace / ".codex" / "config.toml"
    user_text = strip_codex_blocks(config_path.read_text(encoding="utf-8")) if config_path.exists() else ""
    kit_servers = {}
    for name, server in servers.items():
        if re.search(rf"(?m)^\[mcp_servers\.{re.escape(name)}\]", user_text):
            print(f"! MCP-сервер '{name}' уже настроен в .codex/config.toml — оставлен как есть", file=sys.stderr)
            continue
        kit_servers[name] = server
    parts = [part for part in (user_text, render_codex_block(kit_servers).strip() if kit_servers else "") if part]
    if parts:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    elif config_path.exists():
        config_path.unlink()
    return list(kit_servers)


def install(runtime: str, workspace: Path, profiles: list[str], packs: list[str]) -> list[str]:
    servers = collect_servers(profiles, packs)
    previous = read_state(workspace).get(runtime, [])
    if runtime == "claude":
        rendered = {name: render_claude(server) for name, server in servers.items()}
        installed = merge_json_servers(workspace / ".mcp.json", "mcpServers", rendered, previous, {})
    elif runtime == "opencode":
        rendered = {name: render_opencode(server) for name, server in servers.items()}
        installed = merge_json_servers(workspace / "opencode.json", "mcp", rendered, previous, {"$schema": OPENCODE_SCHEMA})
    else:
        installed = merge_codex(workspace, servers)
    write_state(workspace, runtime, installed)
    return installed


def required_env_vars(profiles: list[str], packs: list[str]) -> list[str]:
    servers = collect_servers(profiles, packs)
    return sorted({var for server in servers.values() for var in server.get("env_vars", [])})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install AIKit MCP servers in the runtime's native format")
    parser.add_argument("runtime", choices=RUNTIMES)
    parser.add_argument("--profiles", required=True, help="profile1+profile2")
    parser.add_argument("--packs", default="", help="space-separated pack names")
    parser.add_argument("--workspace", default=".")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profiles = [item for item in args.profiles.split("+") if item]
    packs = args.packs.split()
    installed = install(args.runtime, Path(args.workspace).resolve(), profiles, packs)
    print(" ".join(installed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
