# Repository instructions

Global instruction payloads live in `instructions/`. Editing them changes the
instructions installed on every machine. This file governs this repository only.

Run `cc.py` with the system `python3`, not `uv run`: the interpreter path is
embedded in the startup hooks and must remain stable between install and check.

Vendored skills are reconstructed from `sources.tsv`, then `patches/content/`,
then `patches/compat/shared/`. Keep changes to those skills in the corresponding
patch as well. Target patches under `patches/compat/{claude,codex}/` apply only
when rendering an installation; do not apply them to the shared `skills/` tree.

Verify changes with `python3 -m unittest discover -s tests` and temporary install
roots. Do not use the live user configuration as a test fixture.
