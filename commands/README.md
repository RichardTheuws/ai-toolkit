# Commands

Slash commands for Claude Code. Copy a file to `~/.claude/commands/` (for all
projects) or `.claude/commands/` (one project), then type `/<name>`.

| Command | What it does |
|---|---|
| [`/decision`](decision.md) | Records an architecture decision (ADR) as a dated markdown file in your vault |
| [`/learning`](learning.md) | Records a lesson the same way, and warns when the same lesson keeps coming back |

Both write to plain markdown folders. They work with Obsidian, but don't need it.
Set the location once in your shell profile:

```bash
export VAULT_DIR="$HOME/vault"          # decisions/ and learnings/ go inside
# or separately:
export DECISIONS_DIR="$HOME/notes/adr"
export LEARNINGS_DIR="$HOME/notes/lessons"
```

We have used these daily for months; there are well over a hundred dated
decision records in our own vault by now. The value shows up later, when a
session asks "why is this built this way?" and the answer is one grep away.

See also: [playbooks/obsidian-as-shared-memory.md](../playbooks/obsidian-as-shared-memory.md).

## Make this better

How do you keep decisions findable for your agents? Tell us in the
[discussions](https://github.com/RichardTheuws/ai-toolkit/discussions).
