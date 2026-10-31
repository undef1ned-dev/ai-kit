#!/usr/bin/env python3
"""Regression checks for independent runtime rules and managed updates."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import tomllib
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import rules


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RuntimeRulesTests(unittest.TestCase):
    def test_each_runtime_builds_without_other_runtime_sources(self):
        for runtime in rules.RULES_FILES:
            with self.subTest(runtime=runtime), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                sources = {
                    "base/RULES.md": "# Shared rules\nKeep $literal and /literal unchanged.\n",
                    "profiles/sample/RULES.md": "# Sample stack\nStack requirement.\n",
                    f"adapters/{runtime}/rules.md": f"# {runtime} instructions\n",
                }
                for relative, text in sources.items():
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(text.encode("utf-8"))
                content = rules.render_rules(runtime, ["sample"], root=root)
                self.assertIn("Keep $literal and /literal unchanged.", content)
                self.assertIn("Stack requirement.", content)
                self.assertIn(f"# {runtime} instructions", content)
                self.assertNotIn("\r", content)

    def test_real_shared_sources_are_runtime_neutral(self):
        sources = [rules.ROOT / "base/RULES.md", *rules.ROOT.glob("profiles/*/RULES.md"), rules.ROOT / "templates/profile/RULES.md"]
        for source in sources:
            with self.subTest(source=source):
                content = source.read_text(encoding="utf-8")
                for token in ("Claude", "Codex", ".claude/", ".codex/", "$ARGUMENTS"):
                    self.assertNotIn(token, content)
                skills = {path.parent.name for path in rules.ROOT.glob("**/skills/*/SKILL.md")}
                for skill in skills:
                    self.assertNotRegex(content, r"`/" + re.escape(skill) + r"(?=[` ])")

    def test_missing_runtime_source_fails_instead_of_using_claude(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "base").mkdir()
            (root / "base/RULES.md").write_bytes(b"Shared rules")
            (root / "base/CLAUDE.md").write_bytes(b"Legacy rules")
            with self.assertRaises(FileNotFoundError):
                rules.render_rules("codex", [], root=root)

    def test_plugin_adapter_and_package_use_identical_rules(self):
        plugin = load_script("plugin-init")
        installer = load_script("install-adapter-package")
        builder = load_script("build-adapter-package")
        for profiles in (["vue-nuxt"], ["forge-1-12-java"], ["vue-nuxt", "forge-1-12-java"]):
            for runtime in ("codex", "claude", "antigravity"):
                with self.subTest(runtime=runtime, profiles=profiles), tempfile.TemporaryDirectory() as folder:
                    expected = rules.render_rules(runtime, profiles)
                    self.assertEqual(plugin.render_rules_block(runtime, profiles), f"{rules.BEGIN}\n{expected}{rules.END}\n")
                    if runtime in ("codex", "antigravity"):
                        self.assertEqual(installer.render_agents_md_block(profiles, runtime), plugin.render_rules_block(runtime, profiles))
                    output = Path(folder) / "AIKIT.md"
                    builder.write_combined_instruction({"runtime": runtime}, profiles, output)
                    self.assertEqual(output.read_text(encoding="utf-8"), expected)
                    if runtime == "claude":
                        builder.write_claude_instruction_surface(profiles, output)
                        self.assertEqual(output.read_text(encoding="utf-8"), expected)
        self.assertEqual(installer.AGENTS_MD_BEGIN, rules.BEGIN)
        self.assertEqual(installer.AGENTS_MD_END, rules.END)

    def test_rules_updates_preserve_team_text_and_other_runtime(self):
        plugin = load_script("plugin-init")
        installer = load_script("install-adapter-package")
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            original = f"Team prefix\n{rules.BEGIN}\nLegacy Claude-based text\n{rules.END}\nTeam suffix\n"
            for name in ("AGENTS.md", "CLAUDE.md"):
                (workspace / name).write_bytes(original.encode("utf-8"))
            plugin.merge_rules(workspace, "codex", ["vue-nuxt"])
            self.assertEqual((workspace / "CLAUDE.md").read_text(encoding="utf-8"), original)
            codex = (workspace / "AGENTS.md").read_bytes()
            installer.merge_agents_md(workspace, ["vue-nuxt"], "codex")
            self.assertEqual((workspace / "AGENTS.md").read_bytes(), codex)
            plugin.merge_rules(workspace, "claude", ["forge-1-12-java"])
            self.assertEqual((workspace / "AGENTS.md").read_bytes(), codex)
            for name in ("AGENTS.md", "CLAUDE.md"):
                content = (workspace / name).read_text(encoding="utf-8")
                self.assertTrue(content.startswith("Team prefix\n"))
                self.assertTrue(content.endswith("Team suffix\n"))
                self.assertEqual(content.count(rules.BEGIN), 1)
                self.assertNotIn("Legacy Claude-based text", content)

    def test_codex_rules_use_codex_names_and_model_settings(self):
        content = rules.render_rules("codex", ["vue-nuxt", "forge-1-12-java"])
        self.assertIn("model_reasoning_effort", content)
        self.assertIn("без префикса плагина", content)
        self.assertIn("`$name`", content)
        for token in ("Claude", ".claude/", "CLAUDE.md", "поле `Codex`", "$ARGUMENTS"):
            self.assertNotIn(token, content)

    def test_codex_adapter_install_and_update_preserve_claude_rules(self):
        installer = load_script("install-adapter-package")
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            claude = b"# Existing Claude instructions\nTeam policy.\n"
            (workspace / "CLAUDE.md").write_bytes(claude)
            (workspace / "AGENTS.md").write_bytes(b"# Existing Codex team notes\n")
            for _ in range(2):
                installer.install_package("codex", "vue-nuxt", [], workspace)
                self.assertEqual((workspace / "CLAUDE.md").read_bytes(), claude)
                content = (workspace / "AGENTS.md").read_text(encoding="utf-8")
                self.assertTrue(content.startswith("# Existing Codex team notes\n"))
                self.assertEqual(content.count(rules.BEGIN), 1)
                self.assertIn("Работа в Codex", content)

    def test_repository_codex_maintainer_has_native_model_and_instructions(self):
        source = rules.ROOT / ".codex/agents/aikit-maintainer.toml"
        agent = tomllib.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(agent["name"], "aikit-maintainer")
        self.assertTrue(agent["description"])
        self.assertTrue(agent.get("model"), "the repository maintainer needs an explicit Codex model")
        self.assertNotIn(agent["model"], ("opus", "sonnet", "haiku"))
        self.assertIn(agent["model_reasoning_effort"], ("low", "medium", "high", "xhigh"))
        instructions = agent["developer_instructions"]
        self.assertIn("model_reasoning_effort", instructions)
        for token in ("model: opus", "Codex plugin test", ".Codex", "Codex и Codex"):
            self.assertNotIn(token, instructions)
        skill = (rules.ROOT / ".agents/skills/improve-aikit/SKILL.md").read_text(encoding="utf-8")
        self.assertIn(".codex/agents/aikit-maintainer.toml", skill)
        self.assertNotIn(".claude/agents/", skill)

    def test_installed_codex_agent_names_and_models_match_project_overrides(self):
        plugin = load_script("plugin-init")
        installer = load_script("install-adapter-package")
        model_map = json.loads((rules.ROOT / "adapters/models.json").read_text(encoding="utf-8"))["runtimes"]
        for delivery in ("plugin", "adapter"):
            with self.subTest(delivery=delivery), tempfile.TemporaryDirectory() as folder:
                workspace = Path(folder)
                (workspace / ".aikit").mkdir()
                project = {"agents": {"vue-coder": {"codex": "haiku", "claude": "opus"}}}
                overrides = workspace / ".aikit/models.json"
                overrides.write_bytes(json.dumps(project).encode("utf-8"))
                profiles = ["vue-nuxt", "forge-1-12-java"]
                if delivery == "plugin":
                    names = plugin.write_codex_agents(workspace, profiles, [], [])
                else:
                    installer.install_package("codex", "+".join(profiles), [], workspace)
                    names = [path.stem for path in (workspace / ".codex/agents").glob("*.toml")]
                for name in names:
                    self.assertNotIn(":", name)
                    agent = tomllib.loads((workspace / f".codex/agents/{name}.toml").read_text(encoding="utf-8"))
                    self.assertEqual(agent["name"], name)
                    self.assertNotIn(agent.get("model"), ("opus", "sonnet", "haiku"))
                def read_agent(name):
                    return tomllib.loads((workspace / f".codex/agents/{name}.toml").read_text(encoding="utf-8"))
                coder = read_agent("vue-coder")
                self.assertEqual(coder["model"], model_map["codex"]["haiku"]["model"])
                self.assertEqual(coder["model_reasoning_effort"], model_map["codex"]["haiku"]["model_reasoning_effort"])
                self.assertEqual(read_agent("forge-1-12-java-architect")["model_reasoning_effort"], "medium")
                project["agents"]["vue-coder"] = {"codex": "sonnet", "claude": "haiku"}
                overrides.write_bytes(json.dumps(project).encode("utf-8"))
                if delivery == "plugin":
                    plugin.write_json(workspace / plugin.STATE_FILE, {"runtimes": ["codex"], "profiles": profiles, "packs": [], "codex_agents": names})
                    self.assertEqual(plugin.refresh_agents(workspace), 0)
                else:
                    installer.install_package("codex", "+".join(profiles), [], workspace)
                self.assertEqual(read_agent("vue-coder")["model"], model_map["codex"]["sonnet"]["model"])
                self.assertEqual(read_agent("vue-coder")["model_reasoning_effort"], model_map["codex"]["sonnet"]["model_reasoning_effort"])


if __name__ == "__main__":
    unittest.main()
