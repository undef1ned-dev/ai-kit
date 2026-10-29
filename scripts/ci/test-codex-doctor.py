#!/usr/bin/env python3
"""Readiness checks must preserve project files and distinguish evidence from assumptions."""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("codex_doctor", SCRIPTS / "codex-doctor.py")
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)


class CodexDoctorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.workspace = (self.folder / "project with spaces").resolve()
        self.home = self.folder / "codex-home"
        self.now = dt.datetime(2026, 10, 29, 12, tzinfo=dt.timezone.utc)
        self.version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.write(".aikit/plugin-init.json", json.dumps({"runtimes": ["codex", "claude"], "profiles": ["vue-nuxt"], "packs": [], "codex_agents": ["vue-coder"], "codex_agents_version": self.version}))
        self.write(".aikit/profiles.json", json.dumps({"profiles": {"vue-nuxt": {"agents": {"coder": "vue-coder"}}}}))
        self.write(".aikit/models.json", '{"agents":{"vue-coder":{"codex":"haiku","claude":"opus"}}}')
        fields = doctor.agent_models.resolve("vue-coder", "sonnet", "codex", {"agents": {"vue-coder": "haiku"}})
        self.write(".codex/agents/vue-coder.toml", 'name = "vue-coder"\ndescription = "Coder"\ndeveloper_instructions = "Implement the task"\n' + ''.join(f'{key} = {json.dumps(value)}\n' for key, value in fields.items()))
        self.write("AGENTS.md", "Team rules")
        self.write("CLAUDE.md", "Keep Claude rules")
        self.home.mkdir()
        (self.home / "config.toml").write_bytes((f'[projects.{json.dumps(str(self.workspace))}]\ntrust_level = "trusted"\n').encode("utf-8"))
        self.plugins = [{"name": name, "marketplaceName": "aikit", "installed": True, "enabled": True, "version": self.version, "source": {"source": "local", "path": str(path)}} for name, path in (("aikit", ROOT), ("vue-nuxt", ROOT / "profiles/vue-nuxt"))]
        self.servers = [
            {"name": "context7", "enabled": True, "auth_status": "unsupported", "transport": {"env": {"TOKEN": "DOCTOR_SECRET_SENTINEL"}, "args": ["DOCTOR_SECRET_SENTINEL"]}},
            {"name": "figma", "enabled": True, "auth_status": "logged_in", "transport": {"url": "https://example.invalid/?token=DOCTOR_SECRET_SENTINEL"}},
        ]
        self.cli_calls = []
        self.mark_file = self.folder / "aikit-hooks" / f"run-{hashlib.sha1(str(self.workspace).encode('utf-8')).hexdigest()[:16]}.json"
        self.mark_file.parent.mkdir()
        self.write_mark("codex", self.now)

    def write(self, relative, text):
        path = self.workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def write_mark(self, runtime, when):
        self.mark_file.write_bytes(json.dumps({"runtime": runtime, "runtimes": {runtime: {"events": {"SessionStart": when.isoformat()}}}}).encode("utf-8"))

    def cli(self, codex, args, workspace):
        self.cli_calls.append(args)
        self.assertEqual(workspace, self.workspace)
        if args == ["plugin", "list", "--marketplace", "aikit", "--json"]:
            return {"installed": self.plugins}
        self.assertEqual(args, ["mcp", "list", "--json"])
        return self.servers

    def report(self):
        with patch.object(doctor.shutil, "which", return_value="fake-codex"), patch.object(doctor, "cli_json", side_effect=self.cli), patch.object(doctor, "hook_python", return_value={"status": "ok", "message": "Hook shell Python works"}), patch.object(doctor.tempfile, "gettempdir", return_value=str(self.folder)):
            return doctor.diagnose(self.workspace, codex_home=self.home, now=self.now)

    def checks(self):
        return {item["id"]: item for item in self.report()["checks"]}

    def test_healthy_configuration_is_not_a_claim_of_approved_hooks(self):
        checks = self.checks()
        for name in ("project", "trust", "rules", "agents", "agents.version", "hooks.config", "hooks.history", "mcp.context7", "mcp.figma"):
            self.assertEqual(checks[name]["status"], "ok", checks[name])
        self.assertEqual(checks["hooks.approval"]["status"], "unknown")
        self.assertEqual(checks["hooks.history"]["observed_events"], ["SessionStart"])

    def test_report_does_not_modify_project_or_expose_mcp_secrets(self):
        before = {p.relative_to(self.workspace): p.read_bytes() for p in self.workspace.rglob("*") if p.is_file()}
        report = self.report()
        after = {p.relative_to(self.workspace): p.read_bytes() for p in self.workspace.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertNotIn("DOCTOR_SECRET_SENTINEL", json.dumps(report))
        self.assertEqual(len(self.cli_calls), 2)

    def test_missing_and_stale_agents_are_errors(self):
        self.write(".codex/agents/vue-coder.toml", 'name="vue-coder"\ndescription="Coder"\ndeveloper_instructions="Task"\nmodel="opus"')
        self.assertEqual(self.checks()["agents"]["status"], "error")
        (self.workspace / ".codex/agents/vue-coder.toml").unlink()
        self.assertIn("vue-coder: нет TOML", self.checks()["agents"]["problems"])

    def test_invalid_toml_does_not_hide_other_checks(self):
        self.write(".codex/agents/vue-coder.toml", 'invalid [ DOCTOR_SECRET_SENTINEL')
        checks = self.checks()
        self.assertEqual(checks["agents"]["status"], "error")
        self.assertIn("hooks.history", checks)
        self.assertNotIn("DOCTOR_SECRET_SENTINEL", json.dumps(checks))

    def test_missing_contracts_are_reported(self):
        (self.workspace / ".aikit/profiles.json").unlink()
        self.assertEqual(self.checks()["contracts"]["status"], "error")

    def test_missing_plugin_and_untrusted_project_are_reported(self):
        self.plugins[1]["enabled"] = False
        (self.home / "config.toml").write_bytes((f'[projects.{json.dumps(str(self.workspace))}]\ntrust_level="untrusted"').encode("utf-8"))
        checks = self.checks()
        self.assertEqual(checks["plugin.vue-nuxt"]["status"], "error")
        self.assertEqual(checks["trust"]["status"], "error")

    def test_stale_versions_require_an_update(self):
        self.plugins[0]["version"] = "999.0.0"
        self.assertEqual(self.checks()["agents.version"]["status"], "warning")

    def test_claude_and_legacy_marks_do_not_confirm_codex(self):
        self.write_mark("claude", self.now)
        self.assertEqual(self.checks()["hooks.history"]["status"], "unknown")
        self.mark_file.write_bytes(json.dumps({"runtime": "codex", "events": {"SessionStart": self.now.isoformat()}}).encode("utf-8"))
        self.assertEqual(self.checks()["hooks.history"]["status"], "unknown")

    def test_stale_marks_and_hook_errors_are_distinguished(self):
        self.write_mark("codex", self.now - dt.timedelta(days=2))
        self.assertEqual(self.checks()["hooks.history"]["status"], "warning")
        self.mark_file.write_bytes(json.dumps({"runtimes": {"codex": {"last_error": {"message": "DOCTOR_SECRET_SENTINEL"}}}}).encode("utf-8"))
        check = self.checks()["hooks.history"]
        self.assertEqual(check["status"], "error")
        self.assertNotIn("DOCTOR_SECRET_SENTINEL", json.dumps(check))

    def test_missing_and_global_launcher_marks_are_not_project_failures(self):
        self.mark_file.unlink()
        (self.mark_file.parent / "launch-error.txt").write_bytes(b"DOCTOR_SECRET_SENTINEL")
        check = self.checks()["hooks.history"]
        self.assertEqual(check["status"], "unknown")
        self.assertNotIn("DOCTOR_SECRET_SENTINEL", json.dumps(check))

    def test_mcp_auth_is_configuration_evidence_only(self):
        self.servers[1]["auth_status"] = "not_logged_in"
        self.servers[0]["enabled"] = False
        checks = self.checks()
        self.assertEqual(checks["mcp.figma"]["status"], "warning")
        self.assertEqual(checks["mcp.context7"]["status"], "error")

    def test_hook_marks_keep_errors_separate_between_runtimes(self):
        spec = importlib.util.spec_from_file_location("aikit_hook_doctor_test", ROOT / "base/hooks/aikit_hook.py")
        hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hook)
        with patch.object(hook, "marks_dir", return_value=self.mark_file.parent), patch.object(hook, "runs_in_codex", return_value=True):
            hook.record_run(self.workspace, "PreToolUse", "DOCTOR_SECRET_SENTINEL")
        with patch.object(hook, "marks_dir", return_value=self.mark_file.parent), patch.object(hook, "runs_in_codex", return_value=False):
            hook.record_run(self.workspace, "PreToolUse")
        mark = json.loads(self.mark_file.read_text(encoding="utf-8"))
        self.assertEqual(mark["runtime"], "claude")
        self.assertIn("last_error", mark["runtimes"]["codex"])
        self.assertNotIn("last_error", mark["runtimes"]["claude"])

    def test_python_probe_distinguishes_old_python_and_store_alias(self):
        result = subprocess.CompletedProcess([], 0, "[2, 7, 18]", "DOCTOR_SECRET_SENTINEL")
        with patch.object(doctor.shutil, "which", return_value="C:/Python27/python.exe"), patch.object(doctor.subprocess, "run", return_value=result):
            self.assertEqual(doctor.hook_python()["status"], "warning")
        with patch.object(doctor.shutil, "which", return_value="C:/Users/test/WindowsApps/python.exe"), patch.object(doctor.subprocess, "run") as run:
            self.assertEqual(doctor.hook_python()["status"], "unknown")
            run.assert_not_called()
        with patch.object(doctor.shutil, "which", return_value=None):
            self.assertEqual(doctor.hook_python()["status"], "error")

    def test_unrelated_hook_groups_do_not_confirm_aikit_configuration(self):
        self.plugins[0]["enabled"] = False
        self.write(".codex/hooks.json", json.dumps({"hooks": {event: [{"hooks": [{"command": "other-hook"}]}] for event in doctor.EVENTS}}))
        self.assertEqual(self.checks()["hooks.config"]["status"], "warning")

    def test_relative_trust_entry_is_not_treated_as_confirmed(self):
        (self.home / "config.toml").write_bytes(b'[projects."."]\ntrust_level="trusted"')
        self.assertEqual(self.checks()["trust"]["status"], "unknown")

    def test_adapter_mode_does_not_require_plugin_registration(self):
        (self.workspace / ".aikit/plugin-init.json").unlink()
        self.write(".aikit/package.manifest.json", json.dumps({"adapter_runtime": "codex", "repo_version": self.version}))
        self.write(".aikit/agents/vue-coder.toml", "Canonical source")
        report = self.report()
        self.assertEqual(report["mode"], "adapter")
        checks = {item["id"]: item for item in report["checks"]}
        self.assertEqual(checks["agents"]["status"], "ok")
        self.assertNotIn("plugin.aikit", checks)
        self.assertEqual(self.cli_calls, [["mcp", "list", "--json"]])

    def test_invalid_hook_file_remains_a_distinct_error_in_json(self):
        self.write(".codex/hooks.json", "invalid DOCTOR_SECRET_SENTINEL")
        report = self.report()
        checks = {item["id"]: item for item in report["checks"]}
        self.assertEqual(checks["hooks.file"]["status"], "error")
        self.assertEqual(report["status"], "error")
        self.assertEqual(len(checks), len(report["checks"]))
        self.assertNotIn("DOCTOR_SECRET_SENTINEL", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
