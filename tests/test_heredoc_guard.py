import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "heredoc_guard.py"
spec = importlib.util.spec_from_file_location("heredoc_guard", HOOK)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

BS = chr(92)


class VerdictTests(unittest.TestCase):
    def test_heredoc_with_double_backslash_is_refused(self):
        cmd = "python - <<'PY'\ns = \"" + BS + BS + "b\"\nPY"
        self.assertIsNotNone(guard.verdict(cmd, windows=True))

    # Only the Windows Bash tool loses a backslash, so elsewhere a double one is plain text.
    def test_double_backslash_passes_off_windows(self):
        self.assertIsNone(guard.verdict("printf '%s' 'a" + BS + BS + "b'", windows=False))

    def test_heredoc_without_double_backslash_passes(self):
        cmd = "cat <<'EOF'\nplain text with one " + BS + "n\nEOF"
        self.assertIsNone(guard.verdict(cmd, windows=True))

    # Measured 2026-10-15: outside a heredoc too, printf '%s' 'a\\b' printed a\b, and a\\\\b arrived as a\\b.
    def test_double_backslash_without_heredoc_is_refused(self):
        self.assertIsNotNone(guard.verdict("printf '%s' 'C:" + BS + BS + "Windows'", windows=True))
        self.assertIsNotNone(guard.verdict("node -e 'x(\"" + BS + BS + "d\")'", windows=True))
        self.assertIsNotNone(guard.verdict("grep x <<< 'a" + BS + BS + "b'", windows=True))

    def test_single_backslashes_pass(self):
        self.assertIsNone(guard.verdict("printf 'a" + BS + "nb' && echo $((1 << 2))", windows=True))


class UnquotedHeredocTests(unittest.TestCase):
    """An unquoted heredoc delimiter lets the shell run backtick spans and $(...) in the body."""

    def test_backtick_in_unquoted_heredoc_is_refused(self):
        cmd = "gh pr create --body-file - <<EOF\nRun `julia` first.\nEOF"
        self.assertIsNotNone(guard.verdict(cmd))

    def test_command_substitution_in_unquoted_heredoc_is_refused(self):
        self.assertIsNotNone(guard.verdict("cat <<-END\n\tnow $(date)\n\tEND"))

    def test_quoted_delimiters_pass(self):
        for op in ("<<'EOF'", '<<"EOF"', "<<" + BS + "EOF", "<< 'EOF'"):
            with self.subTest(op=op):
                self.assertIsNone(guard.verdict("cat " + op + "\nRun `julia` and $(date).\nEOF"))

    def test_variable_expansion_passes(self):
        self.assertIsNone(guard.verdict("cat <<EOF\nhome is $HOME and ${USER}\nEOF"))

    def test_text_after_the_terminator_is_not_body(self):
        self.assertIsNone(guard.verdict("cat <<EOF > f\nplain\nEOF\necho `date`"))

    def test_commands_without_an_unquoted_heredoc_pass(self):
        """None of these feeds an unquoted heredoc body to the shell, so none may be refused."""
        for cmd in (
            "mask=$((1 << bits))\nsha=$(git rev-parse HEAD)",
            "python3 - <<'PY'\nx = 1 <<n\nPY\nsha=$(git rev-parse HEAD)",
            "# send via <<EOF\nsha=$(git rev-parse HEAD)",
            "cat <<'A' > a; cat <<B > b\n`date`\nA\nplain $HOME\nB",
            "cat <<E'OF'\n`date`\nEOF",
            "cat <<END-1\nx\nEND-1\necho `date`",
        ):
            with self.subTest(cmd=cmd):
                self.assertIsNone(guard.verdict(cmd, windows=False))

    def test_escaped_spans_and_arithmetic_in_a_body_pass(self):
        for cmd in ("cat <<EOF\nliteral " + BS + "`x" + BS + "` and $HOME\nEOF",
                    "cat <<EOF\nnext: $((n+1)) and " + BS + "$(not run)\nEOF"):
            with self.subTest(cmd=cmd):
                self.assertIsNone(guard.verdict(cmd, windows=False))

    def test_an_escaped_backslash_leaves_the_span_live(self):
        # Bash collapses \\ to \ in an unquoted body, so the $( and the backticks after it run.
        for body in ("C:" + BS + BS + "$(echo RAN)", BS + BS + "`date" + BS + BS + "`", "$(( $(id -u) + 1 ))"):
            with self.subTest(body=body):
                self.assertIsNotNone(guard.verdict("cat <<EOF\n" + body + "\nEOF", windows=False))

    def test_second_unquoted_heredoc_on_a_line_is_read(self):
        self.assertIsNotNone(guard.verdict("cat <<'A' > a; cat <<B > b\nplain\nA\n`date`\nB", windows=False))

    def test_here_string_is_not_a_heredoc(self):
        self.assertIsNone(guard.verdict("grep x <<< \"`date`\""))


class HookOutputTests(unittest.TestCase):
    def run_hook(self, command):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
        return subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True)

    def test_refusal_is_a_pretooluse_deny_with_the_way_out(self):
        res = self.run_hook("cat <<EOF\n`date`\nEOF")
        self.assertEqual(res.returncode, 0)
        out = json.loads(res.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "PreToolUse")
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("<<'EOF'", out["permissionDecisionReason"])

    def test_allowed_command_prints_nothing(self):
        res = self.run_hook("ls -la")
        self.assertEqual((res.returncode, res.stdout), (0, ""))


class SettingsPrecheckTests(unittest.TestCase):
    """The shell pre-check in settings.json starts the hook only for a command with a double backslash."""

    GUARD = '"{{UV}}" run --script "{{REPO}}/hooks/heredoc_guard.py"'

    def run_precheck(self, command, guard):
        """Run the pre-check through `bash -c`, as Claude Code does, with `guard` in place of the uv call."""
        import shutil
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("no bash")
        settings = json.loads((HOOK.parent.parent / "settings.json").read_text(encoding="utf-8"))
        hook = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        self.assertIn(self.GUARD, hook)
        # Claude Code sends Windows paths, which JSON escapes with a double backslash.
        payload = json.dumps({"cwd": "C:" + BS + "Users" + BS + "x", "tool_name": "Bash",
                              "tool_input": {"command": command}})
        return subprocess.run([bash, "-c", hook.replace(self.GUARD, guard)],
                              input=payload, capture_output=True, text=True)

    def test_double_backslash_outside_a_heredoc_reaches_the_hook(self):
        res = self.run_precheck("printf '%s' 'a" + BS + BS + "b'", "echo started")
        self.assertEqual(res.stdout.strip(), "started")

    def test_unquoted_heredoc_reaches_the_hook(self):
        res = self.run_precheck("cat <<EOF\n`date`\nEOF",
                                '"' + Path(sys.executable).as_posix() + '" "' + HOOK.as_posix() + '"')
        self.assertEqual(json.loads(res.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_command_without_double_backslash_does_not_start_the_hook(self):
        for command in ("ls -la", "printf 'a" + BS + "nb'"):
            with self.subTest(command=command):
                res = self.run_precheck(command, "echo started")
                self.assertEqual((res.returncode, res.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
