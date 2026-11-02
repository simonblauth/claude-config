#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""StopFailure hook for rate_limit: wake the session after a usage limit resets.

Claude Code's own wait-and-continue at a usage limit does not start in Remote Control sessions, and a session that
`claude remote-control` serves runs as `--print`, where it is not offered at all
(https://code.claude.com/docs/en/interactive-mode.md#start-a-wait-yourself). Registered with `asyncRewake`, this hook
sleeps until the reset in the background, then exits 2, which wakes the idle session with the message on stderr
(measured 2026-10-29 on 2.1.289: an asyncRewake Stop hook woke an idle served session after 45 s).

The reset comes from the transcript's `quotaLimits.resetsAt`, which 2.1.289 writes on the
rate-limit record. After each sleep the hook reads the transcript again rather than trusting the record it started
on, which can be an earlier limit hit: it stands down when the session has moved past the limit, sleeps again when a
later hit moved the reset, and otherwise wakes the session once per limit record. When Claude Code's own wait in a
terminal session has continued the task before the hook wakes, the hook finds the session moved on and stays quiet.
"""
import json
import sys
import tempfile
import time
from pathlib import Path

# Wake a little after the reset, so the first request does not race it.
MARGIN = 120
# Matches the built-in wait, which does not start for a reset more than 24 hours away.
MAX_WAIT = 24 * 3600
# The hook can start before Claude Code has appended the rate-limit record.
RECORD_POLLS = 10

# One file per limit record that a hook has woken the session for, so a second hook waiting on it stays quiet.
CLAIMS = Path(tempfile.gettempdir()) / "claude-usage-limit-continue"

MESSAGE = "The usage limit has reset. Continue the task you were working on where it stopped."


def last_reply(lines):
    """The last assistant record of the main conversation, skipping subagent and unparsable lines."""
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if record.get("type") == "assistant" and not record.get("isSidechain"):
            return record
    return None


def reset_time(record):
    """The epoch second a rate-limit record says the limit resets, or None for any other record."""
    if record.get("error") != "rate_limit":
        return None
    return (record.get("quotaLimits") or {}).get("resetsAt")


def wait_seconds(resets_at, now):
    """How long to sleep before waking, or None when this reset is not worth a wait."""
    if not resets_at or resets_at <= now or resets_at - now > MAX_WAIT:
        return None
    return resets_at - now + MARGIN


def claim(key):
    """True for the first hook to claim this limit record, False for every later one."""
    CLAIMS.mkdir(parents=True, exist_ok=True)
    try:
        (CLAIMS / key).open("x").close()
    except FileExistsError:
        return False
    return True


def read_reply(path):
    try:
        with open(path, encoding="utf-8") as f:
            return last_reply(f.read().splitlines())
    except OSError:
        return None


def main():
    path = json.load(sys.stdin).get("transcript_path")
    if not path:
        sys.exit(0)
    # An older limit record, whose reset has passed, can still be the last reply until the new one lands.
    for _ in range(RECORD_POLLS):
        record = read_reply(path)
        wait = record and wait_seconds(reset_time(record), time.time())
        if wait:
            break
        time.sleep(1)
    else:
        sys.exit(0)
    while True:
        time.sleep(wait)
        record = read_reply(path)
        resets_at = record and reset_time(record)
        if not resets_at:
            sys.exit(0)
        if resets_at <= time.time():
            break
        wait = wait_seconds(resets_at, time.time())
        if wait is None:
            sys.exit(0)
    if not claim(record.get("uuid") or str(resets_at)):
        sys.exit(0)
    print(MESSAGE, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
