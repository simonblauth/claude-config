---
name: setup-vault
description: Use when the user asks to set up or create a vault, or to update an existing vault's rules, schema, or checker from the template.
---

# Setup vault

`assets/vault/` is the template every vault starts from: its rules, note schema, checker, and pre-commit hook. The vault skills (`brief`, `wrap`, `capture`, `distill`, `report`, `dashboard`) read their formats from these files, and the `dashboard` exporter parses daily notes in the shape the rules give. The vault keeps its rules in `CLAUDE.md`, which the template stores as `vault-rules.md`.

The vault lives at `$VAULT_DIR` (default `~/vault`). Resolve `assets/vault/` against this skill's directory.

## Create

1. Ask the user for the vault's directory and its git remote. The vault holds private content, so the remote must be one only the user can read. A vault can start with no remote and get one later.
2. When the directory exists and holds anything, stop and follow **Update** instead.
3. Copy `assets/vault/` into the directory, hidden files included. Rename `vault-rules.md` to `CLAUDE.md`. Run `chmod +x .githooks/pre-commit`.
4. In the directory, run `git init`, `git config core.hooksPath .githooks`, and `uv run --script tools/check.py`, which must print nothing.
5. Commit everything as `Set up vault from template`. The pre-commit hook runs the checker. With a remote, add it as `origin` and run `git push -u origin HEAD`.
6. When the directory is not `~/vault`, tell the user to set `VAULT_DIR` to it in their shell profile.
7. Offer the `dashboard` skill's **Create**.

The vault is created when the commit exists, the hook runs on commit, and, with a remote, the push succeeded.

## Update

Use this when the template changed after the vault was set up.

1. Pull, as the vault's `CLAUDE.md` says under sync.
2. Diff each template file against its counterpart in the vault, with `vault-rules.md` against `CLAUDE.md`.
3. Show the user each difference. Sections the template lacks, such as `## Dashboard`, belong to this vault: keep them.
4. Apply the differences the user approves in one commit, `Update vault from template`, and push.

The update is complete when every template file matches the vault or the user has declined its difference.
