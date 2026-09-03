# Probes

Commands for the inventory (Phase 1) and the fact-check (Phase 2) of `prune-docs`. Each line of the stale-claim list cites one of these, or a variant of one, together with its output. Run them from the repo root.

## Inventory

Every Markdown file, in three classes. The second and third go into the table flagged user-decides and nothing else in the skill touches them.

```bash
git ls-files -- '*.md'                                  # tracked
git ls-files -o --exclude-standard -- '*.md'            # untracked
git ls-files -o -i --exclude-standard -- '*.md'         # gitignored
```

Per file, size and history:

```bash
wc -lw FILE.md
git log --date=short --format='%ad %h %s' -- FILE.md    # last touch is line 1
git log --oneline -- FILE.md | wc -l                    # commit count
```

### Readership signal (optional, Claude Code transcripts)

Claude Code keeps per-project transcripts as JSON Lines under `~/.claude/projects/<slug>/*.jsonl`, where `<slug>` is the project path with `/` replaced by `-`. A `Read` tool call appears as `"name":"Read","input":{"file_path":"<absolute path>"`. Count reads per doc:

```bash
slug=$(pwd | tr / -)
grep -oh '"name":"Read","input":{"file_path":"[^"]*\.md"' ~/.claude/projects/"$slug"/*.jsonl \
  | sed 's/.*"file_path":"//; s/"$//' | sort | uniq -c | sort -rn
```

This reads an internal log shape. Before trusting a count, confirm the key exists in the log at all:

```bash
grep -c '"name":"Read"' ~/.claude/projects/"$slug"/*.jsonl
```

If that prints zeros, the shape has changed. Report "no readership signal", never "zero reads".

## Fact-check by claim type

| Claim in the doc | Probe | Stale when |
|---|---|---|
| A path or file tree | `test -e PATH`; `find DIR -maxdepth 2 \| sort` against the tree as written | a listed path is missing, or the tree has entries the doc lacks |
| A symbol, function, fixture | `grep -rn 'def SYMBOL\b' src tests` (Python); `grep -rn 'function SYMBOL\b\|SYMBOL(' src` (Julia); `grep -rn 'fn SYMBOL\b' src` (Rust); `grep -rn 'SYMBOL' src --include='*.ts' --include='*.js'` (JS/TS) | zero hits |
| A line-number reference (`file.py:42`) | `sed -n 42p file.py` | the line is not what the doc says it is. Replace with the symbol name regardless of the outcome |
| A CLI flag or subcommand | `CMD --help`; `CMD SUB --help` | the flag is absent or its description differs |
| A flag table or option list | diff the table against `--help` output | any row differs |
| Sample output | re-run the command shown | the output differs in anything the doc's reader would act on |
| A dependency list | `grep -A30 '^\[project\]' pyproject.toml`; `jq .dependencies package.json`; `grep -A30 '^\[deps\]' Project.toml`; `grep -A30 '^\[dependencies\]' Cargo.toml` | a named dependency is missing, or a present one is undocumented and the doc claims completeness |
| A lint or hook list | `grep -E 'id:|repo:' .pre-commit-config.yaml`; the `lint` script in `package.json` | the doc's list and the config disagree |
| A count ("12 modules", "three subcommands") | the command that regenerates the count, recorded next to it | the numbers differ |
| A heading link (`page.md#section`) | `check-docs.sh` anchors row | the slug does not exist in the target |
| A doc page referenced from source comments | `grep -rn 'docs/\|\.md' src tests --include='*.py' --include='*.jl' --include='*.ts'` (extend the include list per ecosystem) | the named page or heading is gone |

Record the exact command you ran, not the template row. The template is for finding the probe; the stale-claim list needs the reproducible one.

## Duplication (Phase 3)

One distinctive verbatim line per suspect block, saved to a file, then:

```bash
grep -cF -f probes.txt -- $(git ls-files -- '*.md')                        # per-file counts
while IFS= read -r line; do
  printf '%4d  %s\n' "$(grep -rFl -- "$line" DOCS | wc -l)" "$line"
done < probes.txt                                                              # files per line
```

`check-docs.sh -p probes.txt` runs the second form and fails any line found in more than one file.

## Pre-state claims (Phase 3)

One grep pattern per claim, matching only that claim: a number, an API name, a mechanism phrase. Save to a file. `check-docs.sh -c claims.txt` fails any pattern with no hit in the doc set; each failure is a claim that has to be either on the stale-claim list or approved at the gate.
