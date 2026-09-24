# Repository instructions

Global instruction payloads live in `instructions/`. Editing them changes the
instructions installed on every machine. This file governs this repository only.

Vendored skills are reconstructed from `sources.tsv`, then `patches/content/`,
then `patches/compat/shared/`. Keep changes to those skills in the corresponding
patch as well. Target patches under `patches/compat/{claude,codex}/` apply only
when rendering an installation; do not apply them to the shared `skills/` tree.

Verify changes with temporary install roots and
`uv run --no-project --python '>=3.11' python -m unittest discover -s tests`.
Do not use the live user configuration as a test fixture.
