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

# `<<` or `<<-`, not the here-string `<<<`, then the whole delimiter word.
OPERATOR = re.compile(r"(?<!<)<<(-?)[ \t]*([^\s;&|<>()]+)")


def heredocs(command: str) -> list[tuple[bool, list[str]]]:
    """Each heredoc bash would read, as (quoted, body lines). Bodies follow the line that opens them, in
    order. A `<<` with no terminator line is arithmetic, a comment or text, not a heredoc to judge."""
    lines = command.split("\n")
    found, i = [], 0
    while i < len(lines):
        opened = [(m.group(1) == "-", m.group(2)) for m in OPERATOR.finditer(lines[i])]
        i += 1
        for strip_tabs, word in opened:
            # Any quote or backslash in the word makes bash read the whole body literally.
            terminator = re.sub(r"[\'\"\\]", "", word)
            for j in range(i, len(lines)):
                if (lines[j].lstrip("\t") if strip_tabs else lines[j]) == terminator:
                    found.append((terminator != word, lines[i:j]))
                    i = j + 1
                    break
    return found


def runs(line: str) -> bool:
    """True when an unquoted heredoc body line holds a backtick or a $( that is not arithmetic $((. Each
    backslash escapes the one character after it, so \\\\$( still runs."""
    i = 0
    while i < len(line):
        c = line[i]
        if c == "\\":
            i += 2
            continue
        if c == "`" or (line.startswith("$(", i) and not line.startswith("$((", i)):
            return True
        i += 1
    return False


def runs_its_body(command: str) -> bool:
    """True when an unquoted heredoc body holds a span the shell would run."""
    return any(not quoted and any(runs(line) for line in body) for quoted, body in heredocs(command))


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
