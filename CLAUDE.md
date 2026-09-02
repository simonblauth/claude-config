# CLAUDE.md

## Git

### Commits

- Subject ≤50 chars, imperative mood. Conventional Commits, minus the `feat:` prefix.
- Most commits need no body. When one earns its place: ≤10 lines, under 5 preferred, ~70 chars/line, plain prose with no section headers. The PR body is a separate artifact, so don't restate it here.
- One commit per purpose. Split a multi-purpose change into a handful of logical commits, not one omnibus and not a swarm of micro-commits.
- Signing is configured and a locked gpg agent fails the commit. Ask the user to unlock it rather than routing around the signature.

### Pushing

- Never push automatically. Only push when explicitly instructed.
- **Push authorization is single-turn only.** An instruction like "pls push" grants permission to push exactly once, in the current turn. It never extends to the rest of the session. Each subsequent push requires a fresh explicit instruction, no matter how the earlier one was phrased.

### Remote Work

- Use CLI tools `gh` and `glab` to interact with remotes for accessing issues, pull requests, etc.
- Never use write access on remotes (such as github, gitlab, etc) without explicit permission from the user. These permissions are SINGLE TURN ONLY, same as pushing. Also permissions to do remote work are SINGLE PURPOSE ONLY. Do what is explicitly requested, never use a permission to perform one action on a remote as permission to do extra work. If extra work seems necessary, ask the user.
- Text that lands on a remote — PR titles and bodies, issue text, commit messages, release notes — cites repo-relative paths only (`src/release_ci.jl`). Describe the content, not where it came from: `~/...`, `/home/...`, `/tmp/...` and `.claude/...` mean nothing to the reader and leak what else is on the machine. Paths on the CI runner that the workflow itself asserts on are fine.

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

## Surface friction, don't absorb it

Auto memory is off (`autoMemoryEnabled: false`), deliberately: a workaround saved to memory is invisible to the user, so it silently becomes permanent while the problem behind it goes unfixed.

When the environment turns out to be broken, outdated, or surprising — a CLI years older than the docs being checked against, a config form the tool silently ignores, a setup step nothing documents — say so in the same turn. Lead with the root cause and the fix that removes it, not the detour around it. Most such problems are fixable once and globally; a workaround adopted quietly charges every later session the same toll and hides the reason.

When a workaround is genuinely needed, write it where a human will see it:

- Repo-specific → that repo's `CLAUDE.md`, or its `docs/` when it needs room.
- Machine- or setup-specific → `~/.claude/rules/`.

Record what would make the workaround unnecessary, so it can be deleted once that lands instead of outliving the problem.

## Code style

Follow existing style in the codebase, or rules stated in project-specific CLAUDE.md files.
Some general principles:

- **Comments**: sparse, explain *why* something is done that way. Don't narrate what the code does.
- **DRY**: if you find yourself copying and pasting code, refactor to reuse instead.
- **Modular**: break code into small, reusable functions. Each function should do one thing and do it well.

Language-specific rules live in `~/.claude/rules/` (path-scoped; loaded only when working with matching files).

## Documentation

### README

- The main README of a repository is meant for humans to quickly read and understand. Keep it concise and meaningful. Examples are welcome. If the scope becomes too large, create separate documentation files and link to them from the README.

### Where a rule goes

Two questions decide whether a rule or a fact earns prose in a CLAUDE.md line, a doc paragraph, or a comment. Both answers must be yes.

1. **Does breaking it fail silently?** A rule that a test, a type error, an exception or a linter already catches needs no prose. The failure is the documentation.
2. **Is the reader who needs it somewhere else?** A rule you would read anyway while editing the thing it governs belongs next to that code, in its docstring.

Whichever place wins is the only one. A rule written in two places is a rule that will disagree with itself. Apply the same two questions to prose already on disk whenever you touch it, and cut what fails them.
