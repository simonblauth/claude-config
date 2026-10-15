---
name: dashboard
description: Use when the user asks to open, refresh, or rebuild the vault dashboard, and when the brief or the wrap has pushed its commit.
---

# Dashboard

The dashboard is a claude.ai artifact of the Dashboard type that shows the vault: today's brief, the week, a project board, and the open tasks. It reads four JSON files that `scripts/export.py` writes from the vault. The vault lives at `$VAULT_DIR` (default `~/vault`). Its `CLAUDE.md` names the dashboard's URL under `## Dashboard`.

The dashboard holds a **snapshot**: it changes only when this skill uploads a new export.

This skill needs the `Artifact` and `ArtifactData` tools. When either is missing, reply "Dashboard not refreshed: no artifact tools in this session." and stop.

## Refresh

1. Pull, as the vault's `CLAUDE.md` says under sync. Take the URL from its `## Dashboard` section. With no URL there, follow **Create** instead.
2. Run `uv run --script scripts/export.py "$VAULT_DIR" <dir>`, with the script path resolved against this skill's directory and `<dir>` a fresh scratch directory. It writes `vault-projects.json`, `vault-tasks.json`, `vault-log.json`, and `vault-days.json`.
3. Read the dashboard's `datasets` collection with `ArtifactData` `list`. Note each document's `version` and its `source.url`, which is the file this run replaces.
4. Upload each of the four files to the dashboard: `Artifact` `publish` with `url`, `asset: true`, and `file_path`, one call per file.
5. In one `ArtifactData` `batch`, `update` each `datasets/<id>` (`projects`, `tasks`, `log`, `days`), pinned with its `if_version`: `source` set to `{kind: "file", url: <new url>, name: <file name>}`, and `updated` set to `{at: <now, ISO 8601 UTC>, by: "Claude"}`.
6. Delete each replaced file: `Artifact` `delete` with `url` and its id (the part of the old `source.url` after `/_blob/`) as `path`. When a delete is refused, go on, and name the files left behind in the reply.
7. Reply in one line: the dashboard's URL, the snapshot time, and the row count of each file.

The refresh is complete when every dataset points at a file uploaded in this run and carries this run's `updated.at`.

## Create

1. Call `Artifact` with `action: "quickstart"` and `intent: "other"`. Publish with the Dashboard `type_url` it names, `title: "Vault"`, and `auto_open: "after_first_write"`. Follow the instructions that result carries for the store's documents.
2. Do steps 2 and 4 of **Refresh**.
3. Write a JSON file `{"text": <contents of assets/index.html>}` to the scratch directory.
4. In one `ArtifactData` `batch`, `set`:
   - `dash/meta` to `{title: "Vault"}`
   - each `datasets/<id>` from `assets/datasets.json`: its `title`, `description`, `schedule`, and `staleAfterHours`, plus `source` and `updated` as in step 5 of **Refresh**
   - `files/index.html` from the JSON file of step 3, through `file_path`
5. Add the URL to the vault's `CLAUDE.md` under `## Dashboard`, then commit and push, as that file says.

The dashboard is created when its page loads all four datasets and the vault records its URL.

## Change the page

The page is `assets/index.html`. It reads the four datasets by id, and their columns are the keys `export.py` writes. Publish a change to the page into the dashboard's `files/index.html` and commit the same change to `assets/index.html`, so a rebuilt dashboard keeps it.
