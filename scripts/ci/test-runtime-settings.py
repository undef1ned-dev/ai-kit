#!/usr/bin/env python3
"""Check native settings, entry points and coexistence without invoking a model."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import hooks_config
import runtime_settings


class RuntimeSettingsTests(unittest.TestCase):
    def test_permissions_are_available_but_never_selected(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            path = workspace / ".codex/config.toml"
            path.parent.mkdir()
            original = 'sandbox_mode="read-only"\napproval_policy="on-request"\n[projects."/team"]\ntrust_level="untrusted"\n'
            path.write_bytes(original.encode())
            runtime_settings.install_codex(workspace)
            first = path.read_bytes()
            runtime_settings.install_codex(workspace)
            self.assertEqual(first, path.read_bytes())
            self.assertEqual(first, original.encode())
            data = tomllib.loads(first.decode())
            self.assertEqual(data["sandbox_mode"], "read-only")
            self.assertEqual(data["approval_policy"], "on-request")
            self.assertEqual(data["projects"]["/team"]["trust_level"], "untrusted")
            self.assertNotIn("default_permissions", data)
            self.assertNotIn("permissions", data)
            data = tomllib.loads((workspace / runtime_settings.TARGET).read_text(encoding="utf-8"))
            self.assertEqual(data["permissions"]["aikit"]["extends"], ":workspace")
            self.assertEqual(data["permissions"]["aikit"]["filesystem"][":workspace_roots"]["**/.env"], "deny")

    def test_team_policy_and_invalid_toml_are_preserved(self):
        for text in ('[permissions.aikit]\nextends=":read-only"\n', 'broken ['):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as folder:
                workspace = Path(folder)
                path = workspace / ".codex/config.toml"
                path.parent.mkdir()
                path.write_bytes(text.encode())
                if text.startswith("broken"):
                    with self.assertRaises(ValueError):
                        runtime_settings.install_codex(workspace)
                else:
                    self.assertTrue(runtime_settings.install_codex(workspace))
                self.assertEqual(path.read_bytes(), text.encode())

    def test_legacy_managed_block_is_removed_without_touching_team_config(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            path = workspace / ".codex/config.toml"
            path.parent.mkdir()
            user = 'sandbox_mode="workspace-write"\napproval_policy="on-request"\n'
            block = runtime_settings.BEGIN + "\n" + runtime_settings.SOURCE.read_text(encoding="utf-8") + runtime_settings.END + "\n"
            path.write_bytes((user + block).encode())
            self.assertTrue(runtime_settings.install_codex(workspace))
            self.assertEqual(path.read_bytes(), user.encode())

    def test_template_is_opt_in_and_team_edits_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            self.assertTrue(runtime_settings.install_codex(workspace))
            self.assertFalse((workspace / ".codex/config.toml").exists())
            template = workspace / runtime_settings.TARGET
            template.write_bytes(b"# team template\n")
            self.assertFalse(runtime_settings.install_codex(workspace))
            self.assertEqual(template.read_bytes(), b"# team template\n")

    def test_selected_legacy_managed_profile_requires_manual_migration(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            path = workspace / ".codex/config.toml"
            path.parent.mkdir()
            text = 'default_permissions="aikit"\n' + runtime_settings.BEGIN + "\n" + runtime_settings.SOURCE.read_text(encoding="utf-8") + runtime_settings.END + "\n"
            path.write_bytes(text.encode())
            self.assertFalse(runtime_settings.install_codex(workspace))
            self.assertEqual(path.read_bytes(), text.encode())

    def test_hooks_keep_both_runtimes_and_user_groups(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            (workspace / ".codex").mkdir()
            user = {"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "team-hook"}]}]}}
            (workspace / ".codex/hooks.json").write_bytes(json.dumps(user).encode())
            hooks_config.install("claude", workspace)
            claude = (workspace / ".claude/settings.json").read_bytes()
            for _ in range(2):
                hooks_config.install("codex", workspace)
            self.assertEqual((workspace / ".claude/settings.json").read_bytes(), claude)
            self.assertEqual(hooks_config.claude_groups()["PreToolUse"]["hooks"][0]["command"], hooks_config.CLAUDE_COMMAND)
            self.assertNotIn("/codex/", hooks_config.CLAUDE_COMMAND)
            data = json.loads((workspace / ".codex/hooks.json").read_text())
            groups = data["hooks"]["PreToolUse"]
            self.assertEqual(len(groups), 2)
            self.assertEqual(groups[0], user["hooks"]["PreToolUse"][0])
            self.assertIn("hooks/codex/aikit_hook.py", groups[1]["hooks"][0]["command"])
            self.assertTrue((workspace / hooks_config.CODEX_HOOK_TARGET).is_file())

    def test_native_entrypoint_marks_codex_without_plugin_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            hooks_config.install("codex", workspace)
            event = {"cwd": str(workspace), "session_id": "native", "hook_event_name": "PreToolUse", "tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** Add File: .env\n+A=1\n*** End Patch"}}
            environment = {**os.environ, "AIKIT_NO_UPDATE_CHECK": "1"}
            for key in ("PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT", "AIKIT_HOOK_RUNTIME"):
                environment.pop(key, None)
            environment["CLAUDE_PROJECT_DIR"] = str(workspace / "unrelated-claude-project")
            run = subprocess.run([sys.executable, str(workspace / hooks_config.CODEX_HOOK_TARGET)], input=json.dumps(event).encode(), capture_output=True, env=environment, cwd=workspace)
            self.assertEqual(run.returncode, 0, run.stderr.decode())
            result = json.loads(run.stdout)
            self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
            status = subprocess.run([sys.executable, str(workspace / hooks_config.CODEX_HOOK_TARGET), "--status"], capture_output=True, env=environment, cwd=workspace)
            data = json.loads(status.stdout)
            self.assertIn("codex", data["runtimes"])


if __name__ == "__main__":
    unittest.main()
