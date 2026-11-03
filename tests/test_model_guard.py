import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "model_guard.py"
spec = importlib.util.spec_from_file_location("model_guard", HOOK)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

POLICY = {"levels": ["low", "medium", "high", "xhigh", "max"], "min_effort": "medium", "max_effort": "xhigh",
          "choices": [["haiku", "medium"], ["opus", "high"], ["opus", "medium"], ["sonnet", "medium"]]}


class VerdictTests(unittest.TestCase):
    def check(self, **tool_input):
        return guard.verdict(tool_input, POLICY)

    def test_a_listed_choice_passes(self):
        self.assertIsNone(self.check(model="opus", effort="high"))

    def test_an_unlisted_pair_is_refused(self):
        self.assertIn("low", self.check(model="opus", effort="low"))
        self.assertIn("haiku@high", self.check(model="haiku", effort="high"))

    def test_effort_outside_the_bounds_is_refused_without_a_model(self):
        self.assertIn("low", self.check(effort="low"))
        self.assertIn("max", self.check(effort="max"))

    def test_a_model_no_task_lists_is_refused(self):
        self.assertIn("fable", self.check(model="fable"))

    def test_a_listed_model_alone_passes(self):
        self.assertIsNone(self.check(model="sonnet"))

    def test_inheriting_passes(self):
        self.assertIsNone(self.check(subagent_type="general-purpose", prompt="x"))


class HookTests(unittest.TestCase):
    def run_hook(self, tool_input, policy=POLICY):
        with tempfile.TemporaryDirectory() as cfg:
            if policy is not None:
                Path(cfg, "model-policy.json").write_text(json.dumps(policy))
            env = {**os.environ, "CLAUDE_CONFIG_DIR": cfg}
            payload = json.dumps({"tool_name": "Agent", "tool_input": tool_input})
            return subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True, env=env)

    def test_refusal_is_a_pretooluse_deny_naming_the_models_section(self):
        res = self.run_hook({"model": "opus", "effort": "low"})
        out = json.loads(res.stdout)["hookSpecificOutput"]
        self.assertEqual((out["hookEventName"], out["permissionDecision"]), ("PreToolUse", "deny"))
        self.assertIn("Models", out["permissionDecisionReason"])

    def test_allowed_call_prints_nothing(self):
        res = self.run_hook({"model": "sonnet", "effort": "medium"})
        self.assertEqual((res.returncode, res.stdout), (0, ""))

    def test_no_policy_file_lets_every_call_through(self):
        res = self.run_hook({"model": "opus", "effort": "low"}, policy=None)
        self.assertEqual((res.returncode, res.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
