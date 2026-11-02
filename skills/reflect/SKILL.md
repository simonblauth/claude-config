---
name: reflect
description: Spawn three parallel review subagents over the active transcript, surface learnings, and route each to a concrete edit on an existing skill. Use when the user says reflect.
---

# Reflect

Read [runtime guidance](references/runtime.md) before following this skill. Resolve all relative paths from this skill directory.

Mine the current conversation for durable learnings, then route them into skill edits.

Invoke when the user says "reflect" or "/reflect". Skip when the conversation is trivial, off-topic, or already covered by an existing skill the parent followed correctly. One-offs are not learnings.

## 1. Locate the active transcript

Use the runtime guidance to locate the active transcript or prepare a digest of this conversation. Never search unrelated conversations. Pass the verified path or digest to each reviewer.

A digest lists, one line each in turn order, the user's prompts and corrections, the tool calls and their results, and the files touched. It states no diagnosis, verdict, or cause. The reviewers judge the session, not your conclusions about it.

## 2. Spawn three reviewers in parallel

Spawn three reviewers with the runtime's subagent tools and model policy. Reviewers need available MCP tools for context lookups referenced in the transcript. Their prompts forbid writes; the parent applies approved edits. If independent subagents are unavailable, report that limitation and perform the three lenses sequentially without claiming independent review.

| Lens | `model` | Prompt template |
|---|---|---|
| Judgment | runtime judgment model | `references/judgment-reviewer.md` |
| Tooling | runtime tooling model | `references/tooling-reviewer.md` |
| Divergent | runtime judgment model | `references/divergent-reviewer.md` |

Pass each template verbatim, substituting the transcript path or digest where marked. Add nothing beside a transcript path, not even a focus note for a long transcript. Collect each reviewer's complete result before synthesis.

## 3. Synthesize

Use a fresh synthesizer with the runtime judgment model, or a clearly labeled sequential synthesis when subagents are unavailable. Retain available MCP access for spot-verifying citations. Use `references/synthesizer.md` verbatim, with each reviewer's full output inlined where marked. The synthesizer returns a structured Accepted / Rejected / Backlog list.

## 4. Structural enforcement check

Move any Accepted item that a lint rule, script, metadata flag, or runtime check would enforce more reliably to Backlog. Prefer an executable check to another prose rule when it can enforce the same lesson.

## 5. Apply

Present the synthesizer's full Accepted / Rejected / Backlog output and wait for explicit approval before applying any Accepted edit. The user picks the subset and may redirect routings. Skill changes affect every future agent in the org. Do not auto-apply.

Present Backlog items as proposals. File them only when the user authorizes that remote write.

Follow each approved row's Routing exactly:

- Trivial existing-skill edit (a one-line bullet, a tightened sentence, a stale fact corrected): the parent does it directly.
- Substantive existing-skill edit (a new section, a new pattern table, more than ~10 lines): use the available skill-authoring skill (`skill-creator` on Codex, `writing-skills` in this collection) and run its draft / test / iterate loop.
- `tune description: <skill path>` (the skill exists but didn't trigger when it should have): hand to the available skill-authoring skill and run its description-optimization loop.
- `new skill: <kebab-name>`: hand creation to the available skill-authoring skill. Do not invent the shape ad hoc.

If your environment ships a SKILL.md validator, run it on every touched skill before declaring done.

## 6. Summarize for the user

Short list, no preamble:

- Edits applied: `<skill path>`. What changed, one line each.
- New skills created: `<skill path>`. One line each (rare).
- Backlog filed to the devex tracker: `<issue title>` (`<tags>`). One line each.
- Dropped: one line per rejected finding + reason from the synthesizer.

## Models

Use the model policy in [runtime guidance](references/runtime.md).
