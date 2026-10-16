# Vault

Private projects, tasks, and research knowledge, kept in markdown and edited by Claude. [CLAUDE.md](CLAUDE.md) holds the rules, [schema.yaml](schema.yaml) the note types, and [docs/design.md](docs/design.md) the reasons behind them.

## Set up a clone

```sh
git clone <remote> ~/vault
cd ~/vault
git config core.hooksPath .githooks
```

The pre-commit hook needs [uv](https://docs.astral.sh/uv/).

## Test the checker

```sh
cd tools && uv run --no-project --with pyyaml python -m unittest test_check
```
