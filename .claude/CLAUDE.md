# CLAUDE.md

Rules for working in this repo. The root `CLAUDE.md` is something else:
`cc.py install` copies it to `~/.claude/CLAUDE.md`, so an edit there changes the
global instructions on every machine that installs from here.

## Running cc.py

Run it with the interpreter that should appear in the hook, `python3 cc.py ...`
on a machine whose `python3` is the system one.

`render_settings()` substitutes `sys.executable` into the SessionStart hook
command. Under `uv run` that resolves to a uv-managed CPython below
`~/.local/share/uv/python/`, which then lands in the installed `settings.json`
and makes every later `check` report `settings.json differs from repo`. This is
the one spot where the global "use uv for Python" rule does not apply.
