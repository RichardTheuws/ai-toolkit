# memory-audit

Scores a project's Claude Code auto-memory green / orange / red, and says what
to fix.

Claude Code loads `MEMORY.md` into every session of a project. Topic files next
to it are read only when relevant. So the index is what you pay for every time;
the topic files are almost free. Left alone, the index slowly turns into a
manual: session notes, version history, long explanations. This script catches
that early.

```
$ memory-audit.sh
=== Memory audit: acme-shop ===
Path:    ~/.claude/projects/-Users-you-code-acme-shop/memory/MEMORY.md
Lines:   112   Files: 19   Sections: 9   Index files: 0

Verdict: ORANGE  - worth a look, not blocking.

Reasons:
  - session sections in MEMORY.md (git log is the session history)
  - MEMORY.md has 112 lines (limit 80)

Suggested actions:
  - Remove the session sections from MEMORY.md; git log already tells that story.
```

## What it checks

| Signal | Orange | Red |
|---|---|---|
| `MEMORY.md` length | > 80 lines | > 150 lines |
| Number of memory files | > 15 | > 30 (> 60 in a router setup) |
| `## Last session` / `## Next session` sections | yes | |
| Sections over 10 lines that are not a pointer list | yes | |
| Version stamps (`v1.2.3`) in section titles | 2+ | |
| `session-*.md` older than 30 days | | > 3 |
| Orphans: files not reachable from `MEMORY.md` | | > 2 |

### Router setups

In a repo with several workstreams we keep `MEMORY.md` as a short router that
points to one index per workstream. A session loads the router plus one index.
The script detects this (two or more files linked from `MEMORY.md` that each link
to three or more memory files) and then measures the **largest index** against
the 80/150 line limits instead of counting files. Files reached through an index
are not orphans.

We added this after the audit stayed red for weeks on a repo whose memory had
just become much leaner. An alarm that always goes off is no alarm; it has to
measure what actually costs context.

## Install and run

```bash
cp memory-audit.sh ~/.claude/scripts/ && chmod +x ~/.claude/scripts/memory-audit.sh
~/.claude/scripts/memory-audit.sh                   # current project
~/.claude/scripts/memory-audit.sh --project-dir ~/code/acme-shop
~/.claude/scripts/memory-audit.sh --json            # for scripts and hooks
```

Run it from the **git root**: auto-memory is keyed on the folder you start Claude
Code in, so a subfolder has its own (often empty) memory and would report a false
green.

We run it at the start of every session (in our `/session-start` command) and only
show something when it isn't green.

Bash 3.2+ (the macOS default), no other dependencies. Honours `CLAUDE_CONFIG_DIR`.

## Test

```bash
bash test_memory_audit.sh   # 8 cases, including a router with 42 files and a path with a space
```

## Background

[playbooks/memory-hygiene.md](../../playbooks/memory-hygiene.md) explains the
rules behind the checks and how to migrate a bloated index.

## Make this better

Different thresholds work better for you? Tell us why in the
[discussions](https://github.com/RichardTheuws/ai-toolkit/discussions).
