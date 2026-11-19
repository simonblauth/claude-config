---
name: review-panel
description: >
  Stress-test a manuscript, report or proposal before it goes to its real
  readers: a panel of independent reviewer subagents, an editor that merges
  them, and a check of every major finding against the source. Runs only on
  /review-panel.
argument-hint: "<document path> [supplement paths] [--size lean|standard|full] [--expert \"...\"] [--reader \"...\"] [--venue \"...\"]"
disable-model-invocation: true
---

# Review panel

A **panel** of reviewers who each read the document cold, through one lens, without seeing each other. An **editor** merges their reports. Then you, who have the source, **verify** what they claim before the user decides anything. The panel finds; it does not know. Two reviewers who agree have found the same passage, not the truth.

## 1. Resolve the brief

The panel needs five things. Take each from the invocation, and infer the rest from a quick read of the document (title, abstract, introduction, conclusions):

| Item | What it is | Example |
|---|---|---|
| Document | the file as its real readers will get it, plus any supplement | the anonymized PDF, not the working copy with notes |
| **Domain expert** | one sentence: the field, and what this person knows cold | "a hydrologist who knows rainfall-runoff modelling, flood-frequency analysis and the calibration of conceptual catchment models" |
| **Intended reader** | one sentence: who is supposed to use the result, and for what | "a municipal engineer who sizes culverts and wants to use the tabulated design flows" |
| Venue | where it goes and the rules that apply there (article type, length, anonymity) | "a hydrology journal, research article, double-anonymized review" |
| Size | lean, standard or full | see step 3 |

A document that spans two fields gets two domain experts, each with its own sentence.

Show the user the brief, with what you inferred marked as inferred, and ask them to confirm or correct it. An expert defined too broadly reviews like a generalist, and the user knows the field better than a quick read does.

**Done when** the user has confirmed the expert, the reader, the venue and the size.

## 2. Build the reading folder

Make a new, empty folder outside any repository, with two parts:

- `input/`: the document and its supplement as PDF, and every page rendered as an image (`pdftoppm -r 100 -png`), one subfolder per file. Reviewers judge figures, tables and layout from the images.
- `reports/`: empty.

The folder is everything a reviewer may read. It holds what a referee receives: no source files, no data, no notes, no earlier reviews. If the document is anonymized, check that the PDF text and its metadata name no author before you start.

**Done when** the folder holds the PDFs and one image per page, and nothing else.

## 3. Seat the panel

| Role | lean | standard | full | Model, from the global `review` row |
|---|---|---|---|---|
| Domain expert (one per field) | x | x | x | strongest choice |
| Methods referee | x | x | x | strongest choice |
| Sceptic | x | x | x | strongest choice |
| Consistency auditor | x | x | x | one step above the default |
| Reader | x | x | x | default |
| Figures and tables | | x | x | default |
| End user | | | x | default |
| Reference checker | | | x | default |

Lean is the floor: three reviewers who can find a wrong result, one who finds the contradictions, and one who tells you whether the abstract works. Take standard when figures and tables carry the result, and full when the document hands its reader something to apply or stands on its citations. A full panel with its editor on a 30-page paper costs about 1.4 million tokens, of which each reviewer takes 100 to 200 thousand; say the expected cost when you confirm the size.

Each reviewer's prompt is [reviewer.md](reviewer.md) with its placeholders filled and the role's block from [roles.md](roles.md) inserted. Resolve both files from this skill's installed directory. Write each filled prompt to a file next to the reading folder, not inside it, and start the reviewer with one line that points at its file: the prompts stay out of your own context, and a reviewer cannot read another one's role.

Start all reviewers in one message, in the background, each with its model and effort passed explicitly. They never see each other's reports: a reviewer who reads another one's notes adopts the first opinion, and the agreement between independent reviewers is the panel's only measure of confidence.

**Done when** every reviewer has returned and its report is in `reports/`. A reviewer whose report lacks the `Read` section or the `Basis` fields did not follow the contract: send it back once with the missing part named. So did a Reader or an End user who viewed fewer page images than the main text has figures and tables.

## 4. The editor

One editor, on the default of the global `judgment` row, with [editor.md](editor.md). It reads all reports and the document, and returns one ranked list of issues, each with a **status**:

- `confirmed`: the editor found it in the document.
- `inconsistent`: two statements in the document disagree, and which one is right is not in the document.
- `needs the authors`: the claim rests on knowledge the document does not contain.
- `reviewer error`: the document already answers it.

**Done when** the editor's letter is in `reports/` and every issue carries a status, the reviewers who raised it, and a cost.

## 5. Verify against the source

This is the step the panel cannot do, and the one the user's decisions rest on. Work every issue the editor ranked essential or important as a **claim**:

- Check it where the truth lives: the data, the analysis code, the cited paper, the configuration. Run the comparison the reviewer could only ask for.
- Record one outcome: **holds** (with the evidence), **does not hold** (with what you checked), or **open** (with what would settle it and who can).
- For a claim that holds, name the cheapest change that answers it. A reviewer's request is one way to resolve an issue, rarely the cheapest.

`inconsistent` and `needs the authors` are the editor telling you where to look, not findings. An inconsistency is often intended; the source says which.

Change nothing in the document yet. With no access to the source, say so and mark every issue open.

**Done when** each essential and important issue has an outcome and evidence you observed in this session.

## 6. Hand back

Give the user, in this order: the editor's decision in two sentences; a table of the verified issues (issue, outcome, evidence, cheapest change, cost); what the panel got wrong; the minor items as a list; and the paths of the letter and the reports. Then ask which changes they want. The user decides what a real referee would insist on and what is out of scope: reviewers ask for more than a paper needs.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The expert is obvious from the title" | Infer it, then ask. The user's one correction is worth more than a reviewer's whole report. |
| "Let the reviewers discuss and converge" | Independent agreement is the signal. Shared notes turn eight readers into one. |
| "Give them the source so they can check" | Then they review the source. A referee gets the document; step 5 has the source. |
| "Three reviewers found it and the editor confirmed it" | Confirmed means found in the document. Whether it is wrong is step 5. |
| "The document contradicts itself, so it is an error" | `inconsistent` is a status, not a verdict. Look up which statement is intended. |
| "The finding is clearly right, apply the fix" | Nothing changes before the user has seen the verified table. |
| "The reviewer asked for a new table, so add one" | Find the cheapest change that answers the claim. |
| "Lean is enough, skip the reader" | The reader is in every size. The abstract is what most people read. |
| "A report without the Basis fields is still useful" | Without them the editor cannot tell seen from guessed. Send it back once. |
