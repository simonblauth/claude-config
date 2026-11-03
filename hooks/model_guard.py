#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""PreToolUse hook for Agent: refuse a subagent whose model or effort is outside the installed model policy.

Claude Code settings can cap effort (`maxEffortLevel`) but cannot set a minimum or forbid a model and effort pair,
so this hook holds the rest of the Models section. `cc.py install` writes the policy it reads to
`model-policy.json` in the Claude config directory. An Agent call that sets neither model nor effort inherits
its parent's, which the policy allows for a subagent that fits no task kind.
"""
import json
import os
from pathlib import Path
import sys


def verdict(tool_input: dict, policy: dict):
    """The reason to refuse the Agent call, or None to let it run."""
    model, effort = tool_input.get("model"), tool_input.get("effort")
    levels = policy["levels"]
    if effort is not None:
        if effort not in levels or not \
                levels.index(policy["min_effort"]) <= levels.index(effort) <= levels.index(policy["max_effort"]):
            return f"effort {effort} is outside {policy['min_effort']} to {policy['max_effort']}"
    listed = {tuple(c) for c in policy["choices"]}
    if model is not None and effort is not None and (model, effort) not in listed:
        return f"{model}@{effort} is not a choice in the Models table"
    if model is not None and model not in {m for m, _ in listed}:
        return f"no task kind in the Models table lists {model}"
    return None


def main() -> None:
    payload = json.load(sys.stdin)
    config = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    try:
        policy = json.loads((config / "model-policy.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    reason = verdict(payload.get("tool_input") or {}, policy)
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": f"This subagent breaks the model policy: {reason}. Start it on its task "
                                        "kind's default or an allowed choice from the Models section of your "
                                        "instructions, or pass neither model nor effort to inherit yours."}}))


if __name__ == "__main__":
    main()
