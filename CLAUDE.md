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

## Work like a scientist

Investigative work belongs to the skills, not to a summary in this file. For debugging, unexpected behavior, "why does X happen?", a performance, security, or correctness assertion, or any report claiming an issue was found, load the skill that owns the discipline and follow its body. `systematic-debugging` owns bugs and unexpected behavior, `tdd` owns implementation, `verification-before-completion` owns claims of done. This file deliberately restates none of them.

**Rigor is proportional:** the skill's full procedure for investigations, bug diagnoses, and perf/security/correctness assertions; lightweight hypothesis-then-verify for small edits.

This is the positive half of "No speculative comments or doc claims" below. Working the skill's procedure earns the right to write a claim that section otherwise forbids.

**Exceptions:**

- **Clearly formulated feature requests.** When the user asks to add or tweak functionality and the request is unambiguous, implement it. Do not hypothesize about whether the feature is warranted or attempt to falsify the premise. "This works" and "done" still require verification, and any bug discovered during implementation gets the full investigative treatment.
- **Creative tasks.** Brainstorming, naming, copy, visual/UX taste, and open-ended design are not falsifiable; the user may say "creative" to opt out. If a task looks creative and the user has not flagged it, ask one clarifying question before reaching for the skills above.

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
