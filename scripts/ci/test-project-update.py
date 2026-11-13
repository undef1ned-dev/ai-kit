#!/usr/bin/env python3
"""Project migrations with real installers and temporary workspaces."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("plugin_init", ROOT / "scripts/plugin-init.py")
init = importlib.util.module_from_spec(spec)
spec.loader.exec_module(init)


class ProjectUpdateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name).resolve()

    def write(self, relative, text):
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def state(self, **data):
        self.write(init.STATE_FILE, json.dumps(data))

    def files(self):
        return {path.relative_to(self.project): path.read_bytes() for path in self.project.rglob("*") if path.is_file()}

    def test_legacy_codex_project_uses_installed_selection_and_preserves_team_files(self):
        self.state(runtimes=["claude", "codex"], profiles=["vue-nuxt"], packs=["devops"], codex_agents=["retired"])
        self.write(".codex/agents/retired.toml", "Retired AIKit agent")
        self.write(".codex/agents/team.toml", "Team agent")
        self.write(".codex/config.toml", 'sandbox_mode = "read-only"\n')
        self.write(".aikit/settings.json", '{"commit":"ask"}')
        self.write(".aikit/memory/INDEX.md", "Team memory")
        self.write(".aikit/models.json", '{"agents":{"vue-coder":{"codex":"opus"}}}')
        self.write(".aikit/profiles.json", '{"profiles":{"vue-nuxt":{"root":"web","commands":{"test":"make test"}}}}')
        self.write("AGENTS.md", "# Team rules\n")
        self.write("CLAUDE.md", "# Claude rules\n")
        before = self.files()
        init.update_project(self.project, "codex", preview=True)
        self.assertEqual(self.files(), before)
        init.update_project(self.project, "codex", preview=False)
        self.assertTrue((self.project / "AGENTS.md").read_bytes().startswith(b"# Team rules\n"))
        self.assertIn(b'[plugins."devops@aikit"]', (self.project / ".codex/config.toml").read_bytes())
        self.assertFalse((self.project / ".codex/agents/retired.toml").exists())
        self.assertIn(b'model_reasoning_effort = "high"', (self.project / ".codex/agents/vue-coder.toml").read_bytes())
        self.assertTrue((self.project / init.runtime_settings.TARGET).exists())
        contract = init.read_json(self.project / ".aikit/profiles.json")["profiles"]["vue-nuxt"]
        self.assertEqual((contract["root"], contract["commands"]["test"]), ("web", "make test"))
        for relative in ["CLAUDE.md", ".aikit/settings.json", ".aikit/models.json", ".aikit/memory/INDEX.md", ".codex/agents/team.toml"]:
            self.assertEqual((self.project / relative).read_bytes(), before[Path(relative)])
        after = self.files()
        init.update_project(self.project, "codex", preview=False)
        self.assertEqual(self.files(), after)
        init.update_project(self.project, "claude", preview=False)
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        state = init.read_json(self.project / init.STATE_FILE)
        self.assertEqual(state["project_versions"], {"claude": version, "codex": version})
        self.assertTrue((self.project / "CLAUDE.md").read_bytes().startswith(b"# Claude rules\n"))

    def test_filters_and_skipped_versions(self):
        journal = {
            "2.0.0": [{"action": "rules"}],
            "1.4.0": [{"action": "codex-agents", "pack": "devops"}, {"action": "rules", "profile": "forge-1-12-java"}],
            "1.3.0": [{"action": "rules", "runtime": "claude"}, {"action": "contracts", "profile": "vue-nuxt"}],
            "Unreleased": [{"action": "contracts"}],
        }
        actual = init.project_updates.select(journal, "1.2.1", "1.4.0", "codex", ["vue-nuxt"], ["devops"])
        self.assertEqual([(version, entry["action"]) for version, entry in actual], [("1.3.0", "contracts"), ("1.4.0", "codex-agents")])

    def test_antigravity_updates_rules_and_local_agents(self):
        self.state(runtime="antigravity", profiles=["vue-nuxt"], antigravity_agents=["retired"])
        self.write("AGENTS.md", "# Team rules\n")
        self.write(".agents/agents/retired.md", "Retired AIKit agent")
        self.write(".agents/agents/team.md", "Team agent")
        self.write(".aikit/models.json", '{"agents":{"vue-coder":{"antigravity":"opus"}}}')
        init.update_project(self.project, "antigravity", preview=False)
        self.assertTrue((self.project / "AGENTS.md").read_bytes().startswith(b"# Team rules\n"))
        self.assertIn(b'`invoke_subagent`', (self.project / "AGENTS.md").read_bytes())
        self.assertEqual((self.project / ".agents/agents/team.md").read_bytes(), b"Team agent")
        self.assertFalse((self.project / ".agents/agents/retired.md").exists())
        self.assertIn(b'subagent: true', (self.project / ".agents/agents/vue-coder.md").read_bytes())
        state = init.read_json(self.project / init.STATE_FILE)
        self.assertEqual(state["antigravity_agents_version"], state["project_versions"]["antigravity"])
        self.assertFalse((self.project / ".codex").exists())

    def test_update_preserves_rules_of_other_runtime_in_shared_file(self):
        self.state(runtimes=["codex", "antigravity"], profiles=["vue-nuxt"])
        original = init.render_rules_block("codex", ["vue-nuxt"])
        self.write("AGENTS.md", original)
        init.update_project(self.project, "antigravity", preview=False)
        self.assertEqual((self.project / "AGENTS.md").read_bytes(), original.encode("utf-8"))

    def test_failed_preparation_leaves_project_unchanged(self):
        self.state(runtime="codex", profiles=["vue-nuxt"], packs=[])
        self.write(".codex/config.toml", "Invalid [")
        before = self.files()
        with self.assertRaises(ValueError):
            init.update_project(self.project, "codex", preview=False)
        self.assertEqual(self.files(), before)

    def test_refuses_unconnected_and_newer_projects(self):
        with self.assertRaisesRegex(ValueError, "нет установки"):
            init.update_project(self.project, "codex", preview=False)
        self.state(runtime="codex", profiles=["vue-nuxt"], project_versions={"codex": "999.0.0"})
        before = self.files()
        with self.assertRaisesRegex(ValueError, "999.0.0"):
            init.update_project(self.project, "codex", preview=False)
        self.assertEqual(self.files(), before)

    def test_failed_write_rolls_back(self):
        self.state(runtime="claude", profiles=["vue-nuxt"])
        self.write("CLAUDE.md", "# Team rules\n")
        before = self.files()
        atomic_write = init.atomic_write

        def fail_state_write(path, data):
            if path == self.project / init.STATE_FILE:
                raise OSError("write failed")
            atomic_write(path, data)

        with patch.object(init, "atomic_write", side_effect=fail_state_write):
            with self.assertRaisesRegex(OSError, "write failed"):
                init.update_project(self.project, "claude", preview=False)
        self.assertEqual(self.files(), before)


if __name__ == "__main__":
    unittest.main()
