#!/usr/bin/env python3
"""Exercise one-step updates with fake CLI responses and the real agent generator."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("update_codex_plugins", SCRIPTS / "update-codex-plugins.py")
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class CodexPluginUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name) / "project with spaces"
        self.workspace.mkdir()
        self.version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.state = {"runtimes": ["claude", "codex"], "profiles": ["vue-nuxt"], "packs": ["devops"], "codex_agents": ["vue-coder", "retired-agent"], "team-field": "keep"}
        files = {
            ".aikit/plugin-init.json": json.dumps(self.state),
            ".aikit/models.json": json.dumps({"agents": {"vue-coder": {"codex": "haiku", "claude": "opus"}}}),
            ".codex/agents/vue-coder.toml": "old managed agent",
            ".codex/agents/retired-agent.toml": "retired managed agent",
            ".codex/agents/team-own.toml": "team-owned agent",
            "AGENTS.md": "team rules",
            "CLAUDE.md": "Claude rules",
            ".aikit/profiles.json": "team contracts",
            ".aikit/settings.json": '{"commit":"ask"}',
            ".aikit/memory/INDEX.md": "team memory",
        }
        for relative, value in files.items():
            path = self.workspace / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value.encode("utf-8"))
        self.calls = []
        self.upgraded = False
        self.fail_upgrade = False
        self.fail_rebuild = False
        self.corrupt_toml = False
        self.mismatch = False
        self.missing = False
        self.original_command = updater.command
        self.output = io.StringIO()

    def snapshot(self):
        return {path.relative_to(self.workspace): path.read_bytes() for path in self.workspace.rglob("*") if path.is_file()}

    def cli(self, argv, workspace):
        self.calls.append(argv)
        if argv[0] != "fake-codex":
            self.assertEqual(Path(argv[1]), ROOT / "scripts/plugin-init.py")
            self.assertNotEqual(workspace, self.workspace)
            if self.fail_rebuild:
                raise updater.UpdateError("test: rebuild failed after marketplace upgrade")
            result = self.original_command(argv, workspace)
            if self.corrupt_toml:
                (workspace / ".codex/agents/vue-coder.toml").write_bytes(b"not valid toml [")
            return result
        if argv[1:4] == ["plugin", "marketplace", "upgrade"]:
            self.assertEqual(argv[4:], ["aikit", "--json"])
            if self.fail_upgrade:
                raise updater.UpdateError("test: marketplace unavailable")
            self.upgraded = True
            return '{}'
        self.assertEqual(argv[1:], ["plugin", "list", "--marketplace", "aikit", "--json"])
        records = []
        for name, folder in (("aikit", ROOT), ("vue-nuxt", ROOT / "profiles/vue-nuxt"), ("devops", ROOT / "packs/devops")):
            if self.missing and name == "devops":
                continue
            records.append({
                "name": name, "marketplaceName": "aikit", "installed": True, "enabled": True,
                "version": ("0.0.2" if name == "devops" and self.mismatch else self.version) if self.upgraded else "0.0.1",
                "source": {"source": "local", "path": str(folder if self.upgraded else self.workspace / "stale cache")},
            })
        return json.dumps({"installed": records, "available": []})

    def run_update(self):
        with patch.object(updater, "command", side_effect=self.cli), contextlib.redirect_stdout(self.output):
            return updater.update(self.workspace, "fake-codex")

    def test_updates_from_fresh_source_and_preserves_team_files(self):
        before = self.snapshot()
        versions = self.run_update()
        self.assertEqual(versions, {name: self.version for name in ("aikit", "vue-nuxt", "devops")})
        self.assertEqual(len(self.calls), 4)
        self.assertFalse((self.workspace / ".codex/agents/retired-agent.toml").exists())
        state = updater.read_json(self.workspace / updater.STATE_FILE)
        self.assertEqual(state["team-field"], "keep")
        self.assertEqual(state["runtimes"], ["claude", "codex"])
        self.assertEqual(state["codex_agents_version"], self.version)
        self.assertEqual(state["codex_plugin_versions"], versions)
        catalog = updater.read_json(self.workspace / updater.CATALOG_FILE)
        self.assertEqual(set(catalog["agents"]), set(state["codex_agents"]))
        for relative, content in before.items():
            if relative not in {updater.STATE_FILE, Path(".codex/agents/vue-coder.toml"), Path(".codex/agents/retired-agent.toml")}:
                self.assertEqual((self.workspace / relative).read_bytes(), content, relative)
        coder = tomllib.loads((self.workspace / ".codex/agents/vue-coder.toml").read_text(encoding="utf-8"))
        models = updater.read_json(ROOT / "adapters/models.json")
        self.assertEqual(coder["model"], models["runtimes"]["codex"]["haiku"]["model"])
        self.assertIn("0.0.1 → " + self.version, self.output.getvalue())
        self.assertIn("новую сессию", self.output.getvalue())

    def test_cli_failure_does_not_change_agents_or_state(self):
        self.fail_upgrade = True
        before = self.snapshot()
        with self.assertRaises(updater.UpdateError):
            self.run_update()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(self.calls), 2)

    def test_missing_plugin_fails_before_marketplace_upgrade(self):
        self.missing = True
        before = self.snapshot()
        with self.assertRaisesRegex(updater.UpdateError, "devops"):
            self.run_update()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.snapshot(), before)

    def test_version_mismatch_does_not_rebuild_agents(self):
        self.mismatch = True
        before = self.snapshot()
        with self.assertRaisesRegex(updater.UpdateError, "Версии"):
            self.run_update()
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(self.snapshot(), before)

    def test_rebuild_failure_keeps_previous_agents(self):
        self.fail_rebuild = True
        before = self.snapshot()
        with self.assertRaises(updater.UpdateError):
            self.run_update()
        self.assertEqual(self.snapshot(), before)

    def test_invalid_toml_is_not_promoted(self):
        self.corrupt_toml = True
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.run_update()
        self.assertEqual(self.snapshot(), before)

    def test_team_agent_collision_is_not_overwritten(self):
        state = dict(self.state, codex_agents=["retired-agent"])
        (self.workspace / updater.STATE_FILE).write_bytes(json.dumps(state).encode("utf-8"))
        before = self.snapshot()
        with self.assertRaisesRegex(updater.UpdateError, "vue-coder"):
            self.run_update()
        self.assertEqual(self.snapshot(), before)

    def test_write_failure_rolls_back_agents_and_state(self):
        original_write = updater.atomic_write
        def fail_state_write(path, data):
            if path == self.workspace / updater.STATE_FILE:
                raise OSError("test: cannot replace state")
            original_write(path, data)
        before = self.snapshot()
        with patch.object(updater, "atomic_write", side_effect=fail_state_write), self.assertRaises(OSError):
            self.run_update()
        self.assertEqual(self.snapshot(), before)

    def test_unconnected_project_does_not_run_cli(self):
        (self.workspace / updater.STATE_FILE).write_bytes(b'{"runtimes":["claude"]}')
        before = self.snapshot()
        with self.assertRaises(updater.UpdateError):
            self.run_update()
        self.assertFalse(self.calls)
        self.assertEqual(self.snapshot(), before)

    def test_invalid_owned_agent_name_does_not_run_cli(self):
        state = dict(self.state, codex_agents=["../team-own"])
        (self.workspace / updater.STATE_FILE).write_bytes(json.dumps(state).encode("utf-8"))
        with self.assertRaises(updater.UpdateError):
            self.run_update()
        self.assertFalse(self.calls)


if __name__ == "__main__":
    unittest.main()
