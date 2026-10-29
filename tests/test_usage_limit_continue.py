import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "usage_limit_continue.py"
spec = importlib.util.spec_from_file_location("usage_limit_continue", HOOK)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

NOW = 1_793_200_000


def reply(uuid, **fields):
    return {"type": "assistant", "uuid": uuid, "isSidechain": False, **fields}


def limit(uuid, resets_at):
    """A transcript record as Claude Code 2.1.289 wrote it for "You've hit your session limit"."""
    return reply(uuid, error="rate_limit", isApiErrorMessage=True,
                 quotaLimits={"status": "rejected", "resetsAt": resets_at, "rateLimitType": "five_hour"})


def lines(*records):
    return [json.dumps(r) for r in records]


class LastReplyTests(unittest.TestCase):
    def test_returns_the_last_main_chain_assistant_record(self):
        transcript = lines(reply("a"), {"type": "user", "uuid": "u"}, reply("b"),
                           {"type": "assistant", "uuid": "side", "isSidechain": True},
                           {"type": "system", "uuid": "s"})
        self.assertEqual(hook.last_reply(transcript)["uuid"], "b")

    def test_skips_blank_and_truncated_lines(self):
        self.assertEqual(hook.last_reply(lines(reply("a")) + ["", '{"type": "assist'])["uuid"], "a")

    def test_none_without_an_assistant_record(self):
        self.assertIsNone(hook.last_reply(lines({"type": "user", "uuid": "u"})))


class ResetTimeTests(unittest.TestCase):
    def test_reads_resets_at_from_a_rate_limit_record(self):
        self.assertEqual(hook.reset_time(limit("a", NOW + 3600)), NOW + 3600)

    def test_none_for_a_normal_reply(self):
        self.assertIsNone(hook.reset_time(reply("a")))

    def test_none_for_a_rate_limit_without_quota_details(self):
        self.assertIsNone(hook.reset_time(reply("a", error="rate_limit")))


class WaitSecondsTests(unittest.TestCase):
    def test_waits_until_the_reset_plus_the_margin(self):
        self.assertEqual(hook.wait_seconds(NOW + 3600, NOW), 3600 + hook.MARGIN)

    def test_no_wait_for_a_reset_already_past(self):
        # Waking at once would hit the limit again and loop.
        self.assertIsNone(hook.wait_seconds(NOW - 1, NOW))

    def test_no_wait_for_a_reset_more_than_a_day_away(self):
        # A weekly limit can reset days out, beyond the hook's timeout.
        self.assertIsNone(hook.wait_seconds(NOW + 24 * 3600 + 1, NOW))
        self.assertEqual(hook.wait_seconds(NOW + 24 * 3600, NOW), 24 * 3600 + hook.MARGIN)


class MainTests(unittest.TestCase):
    def run_main(self, transcript_before, transcript_after, env=None):
        """Run the hook in-process. The transcript changes to `transcript_after` while it sleeps."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            path.write_text("\n".join(transcript_before) + "\n")
            slept = []

            def sleep(seconds):
                slept.append(seconds)
                path.write_text("\n".join(transcript_after) + "\n")

            payload = json.dumps({"hook_event_name": "StopFailure", "error": "rate_limit",
                                  "transcript_path": str(path)})
            stderr = io.StringIO()
            with mock.patch.dict(hook.os.environ, env if env is not None else {hook.OPT_IN: "1"}, clear=True), \
                    mock.patch.object(hook.time, "time", return_value=NOW), \
                    mock.patch.object(hook.time, "sleep", side_effect=sleep), \
                    mock.patch.object(sys, "stdin", io.StringIO(payload)), \
                    mock.patch.object(sys, "stderr", stderr), \
                    self.assertRaises(SystemExit) as exit_:
                hook.main()
            return exit_.exception.code or 0, slept, stderr.getvalue()

    def test_wakes_claude_after_the_reset(self):
        transcript = lines(reply("a"), limit("b", NOW + 600))
        code, slept, message = self.run_main(transcript, transcript)
        self.assertEqual(code, 2)
        self.assertEqual(slept, [600 + hook.MARGIN])
        self.assertIn("Continue the task", message)

    def test_waits_for_the_new_record_behind_a_stale_limit(self):
        # The hook can start before the new rate-limit record lands; until then the last reply is an older limit hit.
        before = lines(limit("old", NOW - 100), {"type": "user", "uuid": "u"})
        code, slept, _ = self.run_main(before, before + lines(limit("new", NOW + 600)))
        self.assertEqual((code, slept), (2, [1, 600 + hook.MARGIN]))

    def test_stays_quiet_when_the_session_moved_on(self):
        # The user prompted after the reset, or a later limit hit started its own wait.
        before = lines(limit("b", NOW + 600))
        code, _, message = self.run_main(before, before + lines(reply("c")))
        self.assertEqual((code, message), (0, ""))

    def test_does_nothing_without_the_opt_in(self):
        transcript = lines(limit("b", NOW + 600))
        code, slept, message = self.run_main(transcript, transcript, env={})
        self.assertEqual((code, slept, message), (0, [], ""))

    def test_does_nothing_for_a_weekly_reset(self):
        transcript = lines(limit("b", NOW + 3 * 24 * 3600))
        code, slept, _ = self.run_main(transcript, transcript)
        self.assertEqual((code, slept), (0, [1] * hook.RECORD_POLLS))


class SettingsTests(unittest.TestCase):
    def test_registered_as_an_async_rewake_stopfailure_hook_for_rate_limits(self):
        settings = json.loads((HOOK.parent.parent / "settings.json").read_text(encoding="utf-8"))
        [group] = settings["hooks"]["StopFailure"]
        [entry] = group["hooks"]
        self.assertEqual(group["matcher"], "rate_limit")
        self.assertIn("hooks/usage_limit_continue.py", entry["command"])
        self.assertTrue(entry["asyncRewake"])
        # Claude Code enforces the timeout on asyncRewake hooks; it must outlast the longest wait.
        self.assertGreater(entry["timeout"], 24 * 3600 + hook.MARGIN)

    def test_runs_as_a_script(self):
        res = subprocess.run([sys.executable, str(HOOK)], input="{}", capture_output=True, text=True,
                             env={"PATH": ""})
        self.assertEqual((res.returncode, res.stdout, res.stderr), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
