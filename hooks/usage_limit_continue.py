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

It acts only where the environment sets CONTINUE_AT_USAGE_LIMIT=1, so it does not double the built-in wait in an
interactive terminal. The reset comes from the transcript's `quotaLimits.resetsAt`, which 2.1.289 writes on the
rate-limit record. Before waking, the hook checks that the session is still stopped at that record: a prompt sent in
the meantime, or a later limit hit with its own wait, makes this wait obsolete.
"""
import json
import os
import sys
import time

OPT_IN = "CONTINUE_AT_USAGE_LIMIT"
# Wake a little after the reset, so the first request does not race it.
MARGIN = 120
# Matches the built-in wait, which does not start for a reset more than 24 hours away.
MAX_WAIT = 24 * 3600
# The hook can start before Claude Code has appended the rate-limit record.
RECORD_POLLS = 10

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


def read_reply(path):
    try:
        with open(path, encoding="utf-8") as f:
            return last_reply(f.read().splitlines())
    except OSError:
        return None


def main():
    if os.environ.get(OPT_IN) != "1":
        sys.exit(0)
    path = json.load(sys.stdin).get("transcript_path") or ""
    # An older limit record, whose reset has passed, can still be the last reply until the new one lands.
    for _ in range(RECORD_POLLS):
        record = read_reply(path)
        wait = record and wait_seconds(reset_time(record), time.time())
        if wait:
            break
        time.sleep(1)
    else:
        sys.exit(0)
    time.sleep(wait)
    latest = read_reply(path)
    if not latest or latest.get("uuid") != record.get("uuid"):
        sys.exit(0)
    print(MESSAGE, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
