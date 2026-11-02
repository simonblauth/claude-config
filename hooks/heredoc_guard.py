#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""PreToolUse hook for Bash: refuse a command that carries a double backslash, or a heredoc that runs its body.

On Windows the Bash tool turns every double backslash of a command into a single one, while a single
backslash passes. That holds in a heredoc body (measured 2026-10-07) and also in single quotes, double quotes and
plain arguments (measured 2026-10-15: printf '%s' 'a\\b' printed a\b, and a\\\\b arrived as a\\b). A Python or
JavaScript string literal needs the double one, so "\\b" arrived as "\b" and wrote a backspace byte into a source file.
The way out is to write the script with the Write tool and run the file, or to edit with the Edit tool; both pass
backslashes unchanged. The hook sees the command before the loss, so it can refuse it.

A heredoc with an unquoted delimiter expands its body, so the shell runs every backtick span and $(...) in it. A
PR body fed to `gh` that way ran the commands its Markdown code spans named.
"""
import json
import re
import sys

DOUBLE_BACKSLASH = "\\\\"

REASON = (
    "This command has a double backslash. On Windows the Bash tool turns every double backslash into a single one, "
    "in a heredoc as well as in quotes and arguments, which silently corrupts string literals, regexes and paths. "
    "Write the script with the Write tool into the scratchpad and run that file, or change files with the Edit tool."
)

UNQUOTED_REASON = (
    "This heredoc has an unquoted delimiter, so the shell runs every backtick span and $(...) in its body. "
    "Quote the delimiter (<<'EOF') to keep the body literal."
)

# `<<` or `<<-`, not the here-string `<<<`, then the delimiter word with its quoting.
HEREDOC = re.compile(r"(?<!<)<<(-?)[ \t]*(['\"]?)(\\?)([A-Za-z_][A-Za-z0-9_]*)\2")


def runs_its_body(command: str) -> bool:
    """True when an unquoted heredoc body holds a backtick or $(...)."""
    lines = command.split("\n")
    for i, line in enumerate(lines):
        for m in HEREDOC.finditer(line):
            strip_tabs, quote, escape, word = m.groups()
            if quote or escape:
                continue
            for body_line in lines[i + 1:]:
                if (body_line.lstrip("\t") if strip_tabs else body_line) == word:
                    break
                if "`" in body_line or "$(" in body_line:
                    return True
    return False


def verdict(command: str, windows: bool = sys.platform == "win32"):
    """The reason to refuse the command, or None to let it run."""
    if windows and DOUBLE_BACKSLASH in command:
        return REASON
    if runs_its_body(command):
        return UNQUOTED_REASON
    return None


def main() -> None:
    payload = json.load(sys.stdin)
    reason = verdict((payload.get("tool_input") or {}).get("command") or "")
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}))


if __name__ == "__main__":
    main()
