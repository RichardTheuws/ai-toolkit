# bash-guard

A Claude Code hook that stops three shell mistakes before they run.

We wrote each of these down as a lesson. Claude still made them again, weeks
later, in a new session. A written lesson is a suggestion; a hook is a rule.
So the lessons became this hook.

| Rule | Blocks | Why it hurts |
|---|---|---|
| R1 | `rsync --delete` to a server without protecting `.env`, or rsync options passed through a string variable | Wiped a production `.env` once. In zsh, `$EXCL="--exclude=a --exclude=b"` is passed as one argument, so the excludes silently do nothing. |
| R2 | `$tag:latest`, `$USER:staff` | zsh reads `:l`, `:s`, `:t`... as modifiers. `$s:latest` becomes something else entirely. Write `${s}:latest`. |
| R3 | `npm test; git push`, or test and deploy on separate lines without `set -e` | The test fails, the push happens anyway. |

When it blocks, Claude gets the reason on stderr and rewrites the command. You
see that happen in the transcript; usually the second attempt is right.

## Install

```bash
mkdir -p ~/.claude/hooks
cp bash-guard.py ~/.claude/hooks/
```

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "python3 ~/.claude/hooks/bash-guard.py", "timeout": 5 }]
      }
    ]
  }
}
```

Requires Python 3.8+, no packages.

## Escape hatches

- One command on purpose: add `# guard-ok: <reason>` to it.
- A whole session: `export CLAUDE_BASH_GUARD=0` before starting Claude Code.

## Test

```bash
python3 test_bash_guard.py   # 34 cases: the real incidents plus look-alikes that must pass
```

## Known limits

- It reads the command text; it does not run a shell parser. Odd quoting can slip through or block a valid command. The tests show where the line is.
- R1 treats any `host:path` destination as a server. Syncing a `dist/`, `build/`, `public/` or `_site/` folder is allowed, because mirroring build output is the point.
- R2 is zsh-specific. In bash, `$s:latest` is harmless, but the `${s}` form is fine in both.

## Make this better

Which mistake does your agent keep repeating? Open an issue or start a
[discussion](https://github.com/RichardTheuws/ai-toolkit/discussions). A new rule
with a test case is the best pull request we can get.
