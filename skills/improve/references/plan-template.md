# Handoff Plan Template

Every plan is written for an executor that has **zero context**: it has not seen the advisor session, the audit, the other plans, or any prior conversation. It may be a smaller/cheaper model. Give it what it cannot find by looking — the problem, the evidence, the outcome, the boundary, and the decisions already made — and leave the *how* to it. The executor reads the live code anyway; implementation steps written today go stale as that code moves, and a plan that dictates them breaks on the first drift.

Three properties make a plan executable by a weaker model:

1. **Self-contained context** — everything needed is in the file: the problem and its evidence, the conventions and constraints, the commands.
2. **A checkable outcome** — done criteria are commands with expected results. The executor never has to *judge* whether it succeeded.
3. **Hard boundaries and escape hatches** — explicit out-of-scope list, and "STOP and report" conditions for when the plan's premise turns out to be false.

**Durable over precise.** Describe behavior, interfaces and contracts, not edits. Cite code by path and symbol (`src/orders/api.ts`, `listOrders()`), never by line number: line numbers rot on the next edit above them. Name the types, signatures and config shapes the change touches; leave the order of edits, the code shape and the test design to the executor, unless a constraint fixes one of them.

File naming: `plans/NNN-short-slug.md`, numbered in recommended execution order.

---

## Template

```markdown
# Plan NNN: <Imperative title — what will be true after this plan>

> **Executor instructions**: This plan states the problem, the outcome and
> the boundary. The steps, the code shape and the tests are yours to choose
> within its constraints. Read the whole plan, confirm on the live code that
> "Current behavior" still holds, then work until every done criterion passes.
> If anything in the "STOP conditions" section occurs, stop and report. When
> done, update the status row for this plan in `plans/README.md` — unless a
> reviewer dispatched you and told you they maintain the index.
>
> **Drift check (run first)**: `git diff --stat <planned-at SHA>..HEAD -- <in-scope paths>`
> If any in-scope file changed since this plan was written, re-check
> "Current behavior" against the live code; if the premise no longer holds,
> treat it as a STOP condition.

## Status

- **Priority**: P1 | P2 | P3
- **Effort**: S | M | L
- **Risk**: LOW | MED | HIGH
- **Depends on**: plans/NNN-*.md, or the issues and open pull requests this plan builds on, as `#N` in this repo or `owner/repo#N` in another (or "none")
- **Base**: <the branch the change targets — only when it is not the default branch; omit otherwise>
- **Category**: bug | security | perf | tests | tech-debt | migration | dx | docs | direction
- **Planned at**: commit `<short SHA>`, <YYYY-MM-DD>
- **Issue**: <GitHub issue URL — only when published via `--issues`; omit otherwise>

## Why this matters

2–5 sentences. The problem, its concrete cost, and what improves when this
lands. Written so the executor (and a human reviewer) understands the
intent — intent is what lets a correct judgment call happen when a detail is off.

## Current behavior

What the code does today, with the evidence — never "as discussed" or "see audit":

- The relevant files and symbols, each with one line on its role:
  - `src/orders/api.ts`, `listOrders()` — order-list endpoint; issues one
    query per order (the N+1)
- A short excerpt at the planned-at commit only where it proves the claim.
- A reproduction: the command, input or test that shows the problem, and
  what it prints.

## Desired behavior

What is true once this lands, including the edge cases and error conditions
that matter. Describe behavior and contracts, not edits:
"`listOrders()` issues a constant number of queries for any page size; an
empty page issues none."

## Constraints

The decisions the executor must respect, each with its reason. Only what
the code does not reveal by itself:

- Interfaces and contracts that must not change: "the public response shape
  stays as is — the v1 clients depend on it".
- Stored formats, schemas and public APIs the change touches, and how far it
  may change them.
- Repo conventions that apply, with one exemplar by path and symbol:
  "Error handling follows the Result pattern — see `src/lib/result.ts` and
  `getUser()` in `src/users/api.ts`. Match it."
- Documented vocabulary or design constraints, quoted from the intent/design
  docs found in recon: the relevant `CONTEXT.md` terms, the `DESIGN.md`
  tokens/components to reuse, or the ADR whose decision this work must stay
  consistent with. Quote the specific lines — the executor has not read
  those docs.

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Install   | `pnpm install`           | exit 0              |
| Typecheck | `pnpm typecheck`         | exit 0, no errors   |
| Tests     | `pnpm test -- <filter>`  | all pass            |
| Lint      | `pnpm lint`              | exit 0              |

(Exact commands from this repo — verified during recon, not guessed.)

## Suggested executor toolkit

(Optional — include only when relevant skills/tools plausibly exist in the
executor's environment. Skip the section otherwise.)

- Skills the executor should invoke if available, and for what:
  "use `vercel-react-best-practices` for the memoization".
- Reference docs worth reading before starting, by path or URL.

## Scope

**In scope** (the only files you should modify):
- `src/orders/api.ts`
- `src/orders/api.test.ts` (create)

**Out of scope** (do NOT touch, even though they look related):
- `src/orders/legacy-api.ts` — deprecated path, scheduled for deletion;
  changing it wastes effort and risks the v1 clients still pinned to it.
- Any change to the public response shape — clients depend on it.

## Git workflow

(Filled from recon — match the repo's observed conventions. The executor's instruction files set the commit message style, so this section names the branch and the commit granularity only.)

- Branch: `advisor/NNN-<slug>` (or the repo's branch-naming convention if one is evident)
- Commit per logical unit.
- Do NOT push or open a PR unless the operator instructed it.

## Done criteria

Machine-checkable outcomes. ALL must hold:

- [ ] A test reproduces <the problem> — it fails on the planned-at commit and
      passes after the change
- [ ] <each edge case from "Desired behavior"> is covered by a test that passes
- [ ] `pnpm typecheck` exits 0
- [ ] `pnpm test` exits 0
- [ ] `grep -rn "<old pattern>" src/` returns no matches
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:

- "Current behavior" no longer describes the live code (the codebase has
  drifted since this plan was written).
- The desired behavior appears to require touching an out-of-scope file or
  breaking a constraint.
- You discover the assumption "<key assumption>" is false.

## Maintenance notes

For the human/agent who owns this code after the change lands:

- What future changes will interact with this (e.g. "if pagination is added
  to this endpoint, the query batching must be revisited").
- What a reviewer should scrutinize in the PR.
- Any follow-up explicitly deferred out of this plan (and why).
```

---

## Index file: `plans/README.md`

Written once by the advisor after all plans, updated by executors:

```markdown
# Implementation Plans

Generated by the improve skill on <date>. Execute in the order below unless
dependencies say otherwise. Each executor: read the plan fully before starting,
honor its STOP conditions, and update your row when done.

## Execution order & status

| Plan | Title | Priority | Effort | Depends on | Status |
|------|-------|----------|--------|------------|--------|
| 001  | ...   | P1       | S      | —          | TODO   |
| 002  | ...   | P1       | M      | 001        | TODO   |

Status values: TODO | IN PROGRESS | DONE | BLOCKED (with one-line reason) | REJECTED (with one-line rationale — finding fixed independently or approach abandoned)

## Dependency notes

- 002 requires 001 because <reason>.

## Findings considered and rejected

- <finding>: not worth doing because <one line>. (So nobody re-audits it.)
```

## Quality bar — check before finishing each plan

- Could a model that has never seen this repo execute this with only the plan file and the repo? If the plan relies on knowledge from the advisor session, inline that knowledge.
- Is every done criterion a command with an expected result, not a judgment ("make sure it works")?
- Does the plan name the files, symbols and interfaces involved, not "the relevant module", and cite no line numbers?
- Does it state outcomes and constraints, and leave the steps and test design to the executor unless a constraint fixes them?
- Are the STOP conditions specific to this plan's actual risks, not boilerplate?
- Would a reviewer reading only "Why this matters" + "Done criteria" understand what they're approving?
- No secret values anywhere in the file — locations and credential types only.
- "Planned at" SHA is filled in and the in-scope paths in the drift check match the Scope section.
