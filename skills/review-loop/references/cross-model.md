# Cross-model review dispatch

`--reviewer claude` or `--reviewer codex` runs each round in that runtime's CLI instead of a subagent, so a model family other than the author's reads the diff.

## Every round

1. Check that the CLI is on `PATH` (`command -v claude` or `command -v codex`). When it is missing, or its first run fails on authentication, report that and stop the loop. Falling back to a self-review is not a clean independent round.
2. Write the filled reviewer prompt to a file under a fresh `mktemp -d`, outside the target repository, so the reviewer does not review its own prompt.
3. Run one new process with the command below. A round can take minutes, so run it in the background when the runtime supports that, and wait for it to exit.
4. The output file is the round's result, read under reviewer.md's rules. A non-zero exit or an empty file is a failed round, not a clean one; report it, and do not count a `No findings.` that never arrived.

Both commands block writes to the repository, so a reviewer may be unable to run a suite that writes caches or build output. Its findings then rest on reading, which reviewer.md allows.

## Codex reviews

    codex exec --sandbox read-only --ephemeral -C <REPO> -o <out file> - < <prompt file>

Per the [non-interactive docs](https://learn.chatgpt.com/docs/non-interactive-mode): `-` reads the prompt from standard input, `read-only` is also `exec`'s default sandbox and is passed anyway so the command says what it relies on, `--ephemeral` skips persisting session files, `-C` sets the working directory, and `-o` writes the final message to the file. Leave the model to the user's Codex configuration.

## Claude reviews

    (cd <REPO> && claude -p --permission-mode dontAsk \
      --disallowedTools Edit Write NotebookEdit \
      --no-session-persistence < <prompt file> > <out file>)

`dontAsk` auto-denies every tool call that would prompt and still allows reads, read-only Bash and the user's allow rules, per the [permission modes docs](https://code.claude.com/docs/en/permission-modes). `--disallowedTools` removes the edit tools outright. On Claude Code 2.1.221 this pair ran `git status` and denied both the `Write` tool and a `printf > file` redirect. Leave `--model` off, so the reviewer runs on the user's configured model.
