#!/usr/bin/env python3
"""Verify native Codex inventory, source isolation and delivered content."""

import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
import agent_models
import codex_content


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


builder = module("native_builder", "build-adapter-package.py")
plugin = module("native_plugin", "plugin-init.py")
plugins = module("native_plugins", "build-plugins.py")
installer = module("native_installer", "install-adapter-package.py")
SOURCES = [ROOT / "base", *sorted((ROOT / "profiles").iterdir()), *sorted((ROOT / "packs").iterdir())]
PROFILES = [path.name for path in SOURCES if path.parent.name == "profiles"]
PACKS = [path.name for path in SOURCES if path.parent.name == "packs"]


class NativeContentTests(unittest.TestCase):
    def test_inventory_and_metadata_match_logical_roles(self):
        for source in SOURCES:
            with self.subTest(source=source):
                native = codex_content.agents([source])
                self.assertEqual(set(native), {p.stem for p in (source / "agents").glob("*.md")})
                expected = {p.parent.name for group in ("skills", "plugin-skills") for p in (source / group).glob("*/SKILL.md")}
                self.assertEqual({p.name for p in codex_content.skills([source], plugin=True)}, expected)
                for skill in codex_content.skills([source], plugin=True):
                    raw, body = builder.split_frontmatter((skill / "SKILL.md").read_text(encoding="utf-8"))
                    metadata = builder.parse_frontmatter(raw)
                    self.assertEqual(set(metadata), {"name", "description"})
                    self.assertEqual(metadata["name"], skill.name)
                    self.assertTrue(metadata["description"] and body.strip())
                catalog = codex_content.catalog([source])
                self.assertEqual(set(catalog["agents"]), set(native))
                self.assertEqual(set(catalog["skills"]), expected)
                for name, path in native.items():
                    definition = codex_content.read_agent(path)
                    block = catalog["agents"][name].get("output_block")
                    self.assertTrue(block)
                    self.assertIn(block, definition["developer_instructions"])
                    self.assertIn(definition["model_reasoning_effort"], {"low", "medium", "high", "xhigh", "max", "ultra"})
                    self.assertNotIn("sandbox_mode", definition)
                    for dependency in catalog["agents"][name].get("depends_on", []):
                        self.assertIn(dependency, native | codex_content.agents([ROOT / "base"]))

    def test_native_prompts_do_not_reference_foreign_instructions(self):
        forbidden = re.compile(r"CLAUDE\.md|\.claude/|\$ARGUMENTS|code-review|base/agents/|profiles/\*/agents/|packs/\*/agents/")
        for source in SOURCES:
            paths = [*codex_content.agents([source]).values(), *(p / "SKILL.md" for p in codex_content.skills([source], plugin=True))]
            for path in paths:
                with self.subTest(path=path):
                    text = path.read_text(encoding="utf-8")
                    self.assertIsNone(forbidden.search(text))

    def test_explicit_invocation_and_assets_are_present(self):
        for source in SOURCES:
            for native in codex_content.skills([source], plugin=True):
                group = "plugin-skills" if native.parent.name == "plugin-skills" else "skills"
                original = source / group / native.name
                for asset in original.rglob("*"):
                    if asset.is_file() and asset.name != "SKILL.md":
                        self.assertEqual((native / asset.relative_to(original)).read_bytes(), asset.read_bytes(), str(asset))
                head = original.joinpath("SKILL.md").read_text(encoding="utf-8").split("\n---", 1)[0]
                if "disable-model-invocation: true" in head:
                    self.assertIn("allow_implicit_invocation: false", (native / "agents/openai.yaml").read_text(encoding="utf-8"))

    def test_plugin_and_adapter_build_without_reading_claude_prompts(self):
        original = Path.read_text

        def read(path, *args, **kwargs):
            if path.is_relative_to(ROOT):
                relative = path.relative_to(ROOT)
                if "codex" not in relative.parts and any(part in {"agents", "skills", "plugin-skills"} for part in relative.parts) and relative.parts[0] in {"base", "profiles", "packs"}:
                    raise AssertionError(f"Codex read another runtime's prompt: {relative}")
            return original(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as folder, patch.object(Path, "read_text", read):
            workspace = Path(folder)
            bundle = builder.build_package("codex", "+".join(PROFILES), PACKS, workspace / "bundle")
            plugin.write_codex_agents(workspace / "plugin", PROFILES, PACKS, [])
            for name, source in codex_content.agents(SOURCES).items():
                self.assertEqual((bundle / ".codex/agents" / f"{name}.toml").read_bytes(), source.read_bytes())
                self.assertEqual((workspace / "plugin/.codex/agents" / f"{name}.toml").read_bytes(), source.read_bytes())
            for source in codex_content.skills(SOURCES):
                self.assertEqual((bundle / ".agents/skills" / source.name / "SKILL.md").read_bytes(), (source / "SKILL.md").read_bytes())
            self.assertEqual(json.loads((bundle / ".aikit/agent-catalog.json").read_text(encoding="utf-8")), codex_content.catalog(SOURCES))
        core = plugins.codex_manifest(plugins.plugin_specs()[0])
        self.assertEqual(core["skills"], ["./base/codex/skills/", "./base/codex/plugin-skills/"])

    def test_missing_native_layer_has_no_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)
            (source / "agents").mkdir()
            (source / "agents/fallback.md").write_bytes(b"Should never be read")
            with self.assertRaisesRegex(ValueError, "no fallback"):
                codex_content.agents([source])
            with self.assertRaises(FileNotFoundError):
                codex_content.catalog([source])

    def test_native_defaults_ignore_legacy_tiers(self):
        with patch.object(agent_models, "kit_agent_tiers", side_effect=AssertionError("legacy tiers read")):
            self.assertEqual(agent_models.resolve("vue-architect", "haiku", "codex", {}), agent_models.codex_defaults()["vue-architect"])
            with tempfile.TemporaryDirectory() as folder:
                workspace = Path(folder)
                target = workspace / ".codex/agents/vue-coder.toml"
                target.parent.mkdir(parents=True)
                target.write_bytes((ROOT / "profiles/vue-nuxt/codex/agents/vue-coder.toml").read_bytes())
                (workspace / ".aikit").mkdir()
                (workspace / ".aikit/models.json").write_bytes(b'{"agents":{"vue-coder":{"codex":"test-native-model","claude":"opus"}}}')
                agent_models.apply("codex", workspace)
                result = tomllib.loads(target.read_text(encoding="utf-8"))
                self.assertEqual(result["model"], "test-native-model")
                self.assertEqual(result["model_reasoning_effort"], "medium")

    def test_legacy_install_migrates_and_tracks_agents_without_removing_team_files(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            files = {
                ".aikit/package.manifest.json": '{"adapter_runtime":"codex"}',
                ".aikit/agents/retired-agent.md": "old managed source",
                ".codex/agents/retired-agent.toml": "old managed agent",
                ".codex/agents/team-own.toml": "team native agent",
                ".codex/agents/team-own.md": "team legacy agent",
                ".agents/skills/team-own/SKILL.md": "team skill",
                ".claude/agents/team-own.md": "Claude agent",
            }
            for relative, text in files.items():
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(text.encode("utf-8"))
            installer.install_package("codex", "vue-nuxt", ["devops"], workspace)
            self.assertFalse((workspace / ".codex/agents/retired-agent.toml").exists())
            self.assertFalse(list((workspace / ".aikit/agents").glob("*.md")))
            installer.install_package("codex", "vue-nuxt", [], workspace)
            self.assertFalse((workspace / ".codex/agents/devops-engineer.toml").exists())
            for relative, text in files.items():
                if relative.startswith((".codex/agents/team-own", ".agents/skills/team-own", ".claude/")):
                    self.assertEqual((workspace / relative).read_bytes(), text.encode("utf-8"))
            manifest = json.loads((workspace / ".aikit/package.manifest.json").read_text(encoding="utf-8"))
            self.assertIn(".codex/agents/vue-coder.toml", manifest["native_paths"])


if __name__ == "__main__":
    unittest.main()
