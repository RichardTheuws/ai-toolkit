# compact-recovery

After Claude Code compacts a long conversation, the summary sometimes loses the
practical details: which branch, what is uncommitted, what was just committed.
This hook puts them back right after compaction.

```
[After compaction] Working directory: /Users/you/code/acme-shop
Branch: main
3 uncommitted file(s); run git status before continuing.
Recent commits:
4e61bd6 fix: rounding in invoice totals
…
Re-read MEMORY.md and the task list before you continue.
```

## Install

```bash
cp compact-recovery.js ~/.claude/hooks/
```

In `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "compact", "hooks": [{ "type": "command", "command": "node ~/.claude/hooks/compact-recovery.js", "timeout": 5 }] }
    ]
  }
}
```

Node 18+, no packages.

## A mistake we made first

We first hung this on `PreCompact`. It looked like it worked, but the output of a
PreCompact hook only steers the compaction summary; it is not added to the
context. `SessionStart` with matcher `compact` fires right after compaction and
does add its `additionalContext`.

## Make this better

What do you want Claude to know after a compaction? Share it in the
[discussions](https://github.com/RichardTheuws/ai-toolkit/discussions).
