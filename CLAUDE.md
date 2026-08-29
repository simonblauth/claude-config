# CLAUDE.md

## Git

### Commits

- Subject ≤50 chars, imperative mood. Conventional Commits, except for the `feat:` prefix.
- Body: hard cap 10 lines, ~70 chars/line. <5 lines preferred. Most commits need no body at all.
- Exception: a genuinely complicated change may use full sentences — but still ≤10 lines total.
- No `Summary:` / `Context:` / `Verification:` section headers in commit bodies. The PR body is a separate artifact; don't duplicate it into commits.
- Commit by purpose/feature. When implementing a larger plan that is multi-step or covers multiple purposes, split it into a few logical commits instead of one omnibus commit. Don't go overboard — a handful of purposeful commits, not a gazillion micro-commits.
- Never commit without signing. If the gpg agent is locked, prompt the user to unlock it instead of skipping the signature.
- Omit claude co-authorship lines from commits.

### Pushing

- Never push automatically. Only push when explicitly instructed.
- **Push authorization is single-turn only.** An instruction like "pls push" grants permission to push exactly once, in the current turn. It never extends to the rest of the session. Each subsequent push requires a fresh explicit instruction, no matter how the earlier one was phrased.

### Remote Work

- Use CLI tools `gh` and `glab` to interact with remotes for accessing issues, pull requests, etc.
- Never use write access on remotes (such as github, gitlab, etc) without explicit permission from the user. These permissions are SINGLE TURN ONLY, same as pushing. Also permissions to do remote work are SINGLE PURPOSE ONLY. Do what is explicitly requested, never use a permission to perform one action on a remote as permission to do extra work. If extra work seems necessary, ask the user.

## Secrets

- Never read, print, log, or commit credential material: `.env*` files, `*.pem`, `*.key`, SSH keys, API tokens, connection strings, Key Vault values.
- Refer to secrets by name or environment variable, never by value. If a task appears to require a secret's actual value, stop and ask the user instead of retrieving it.

## Work like a scientist — hypothesis → falsify → reproduce → record

Default for investigative work: debugging, unexpected behavior, "why does X happen?", performance/security/correctness assertions, and **any report claiming an issue was found**. State the hypothesis (from code evidence, research, or the prompt). Research deeper before acting. Run an experiment designed to *falsify* it, not confirm it — assumptions are hypotheses, never conclusions. Reproduce the result before trusting it. Record what was run and observed (commands, outputs, file:line). No claim, fix, or "done" without an experiment that survived a falsification attempt.

Route through existing skills as the mechanism, don't reinvent: `systematic-debugging` (bugs/unexpected behavior), `tdd` (features/fixes), `verification-before-completion` (before claiming done).

**Rigor is proportional:** full loop (reproduce + record) for investigations, bug diagnoses, perf/security/correctness assertions; lightweight hypothesis-then-verify for small edits.

This is the positive half of "No speculative comments or doc claims" below — the procedure that earns the right to write a claim that section otherwise forbids.

**Exceptions:**

- **Clearly formulated feature requests.** When the user asks to add or tweak functionality and the request is unambiguous, do not put the request itself through the loop — no hypothesizing about whether the feature is warranted or attempting to falsify the premise. Implement it. The loop still applies to claims made along the way: "this works" / "done" still requires verification (lightweight — run it, check the output), and any bug discovered *during* implementation goes back through the full loop.
- **Creative tasks.** Brainstorming, naming, copy, visual/UX taste, open-ended design are not falsifiable — the user may say "creative" to opt out. If a task looks creative and the user hasn't flagged it, ask one clarifying question before defaulting to the scientific loop.

## No speculative comments or doc claims

Every comment, docstring, README line, CHANGELOG entry, PR description, and proposal claim must be backed by evidence personally observed in this session (grep output, file read, command result, official doc). If a concrete source can't be cited, the claim does not belong in the artifact — delete the speculation, keep only the verified *what*. Attributions like "races destructor in package X" or "comes from native binding Y" are speculation unless that package's source was actually read. Conversational claims to the user are fine; written-to-disk claims are not.

## Verify before asserting tool behavior

When the user asks about the behavior, options, flags, defaults, or capabilities of a CLI, API, library, or service — typical phrasings: "is there a way to…", "can I do…", "does X support…", "what flag for…", "how does X behave when…" — verify before answering. Do not rely on training-data recall.

Acceptable verification, in order of preference:

1. Run `--help` / `man` / equivalent locally via the shell tool.
2. Fetch official docs (WebFetch) or search (WebSearch).
3. Read the tool's source if it's available locally.

If none of those are possible in the current environment, say so explicitly and hedge ("I can't verify this from here — based on training data, …") rather than asserting with confidence. If the user pushes back on a factual claim, do not double down — verify and correct.

## Code style

Follow existing style in the codebase, or rules stated in project-specific CLAUDE.md files.
Some general principles:

- **Comments**: sparse, explain *why* something is done that way. Don't narrate what the code does.
- **DRY**: if you find yourself copying and pasting code, refactor to reuse instead.
- **Modular**: break code into small, reusable functions. Each function should do one thing and do it well.

Language-specific rules live in `~/.claude/rules/` (path-scoped; loaded only when working with matching files).

## Documentation

- The main README of a repository is meant for humans to quickly read and understand. Keep it concise and meaningful. Examples are welcome. If the scope becomes too large, create separate documentation files and link to them from the README.
