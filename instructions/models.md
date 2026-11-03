## Models

Choose each subagent's model and effort for the work in front of it, from its task kind's row below, and {{spawn}}. The default fits the typical task. Weigh every task in both directions:

- **Stronger**, a bigger model or more effort: the implementation looks complex or spans several modules; the decisions matter or are hard to undo, such as a stored or wire format, a public API or security; the work is open-ended, such as design, research or an unclear spec; or an earlier attempt or review round fell short.
- **Smaller**, a smaller model or less effort: the work is simple and well defined, such as a docs or config change, a rename, a one-file fix with a clear test, a search for a precise target, or re-checking one specific claim.

Hand broad reading, such as searching a codebase, surveying files, or reading logs and transcripts, to an `explore` subagent, and keep your own context to what you act on: whatever you read yourself is re-read on every later call.

Name the choice and the reason in the subagent's report. Use nothing outside the table. A subagent that fits no kind, such as one that tests how a model behaves with a skill, inherits your model and effort: pass neither. No effort goes below `{{min_effort}}` or above `{{max_effort}}`.{{runtime_note}}

| Task | Default | Also allowed |
|---|---|---|
{{rows}}

- `explore`: searching and reading broadly.
- `audit`: reading code or a transcript to report findings: improve's and architecture review's auditors, reflect's reviewers, dispatched improve and architecture runs.
- `implement`: changing code: issue-to-pr runs, improve's executor.
- `review`: reviewing a diff: each review-loop round.
- `design`: designing or planning: interfaces, design-it-twice, plans.
- `judgment`: deciding: triage, reflect's synthesizer, a dispatcher's own decisions.

{{cross}}
