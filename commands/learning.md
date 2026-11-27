---
description: Record a lesson (gotcha, success, failure, anti-pattern) in your notes vault
argument-hint: "[project] [title]"
---

# /learning: record a lesson

Write one lesson as a markdown file, so the next session (or the next project)
does not have to learn it again.

## Where it goes

1. Folder: `$LEARNINGS_DIR` if set, else `$VAULT_DIR/learnings`, else `~/vault/learnings`.
   Check with `echo "${LEARNINGS_DIR:-${VAULT_DIR:-$HOME/vault}/learnings}"`. Create it if missing.
2. File name: `<YYYY-MM-DD>-<title-slug>.md`. Never overwrite; add `-2`, `-3`, ...

## What to ask

Arguments: `$ARGUMENTS` (optional project slug, then title).

Fill in what you can from the conversation first, then ask for the rest **in one
message**, numbered:

1. Project slug
2. Title
3. Type:
   - `gotcha`: a non-obvious technical detail (API quirk, version clash)
   - `success`: something that worked and is worth repeating
   - `failure`: something that went wrong once
   - `anti-pattern`: a mistake that would go wrong in other projects too
4. What happened (1-3 sentences, concrete)
5. What we learned, as an instruction ("always X", "never Y")
6. Root cause: not "I forgot", but what in the system made it easy to forget
7. How to apply: the trigger. When should this lesson come to mind?

## File format

```markdown
---
type: learning
project: <slug>
date: <YYYY-MM-DD>
learning_type: <type>
title: "<title>"
tags: [learning, <slug>, <type>]
---

# <title>

**What happened**: <text>

**Lesson**: <text>

**Root cause**: <text>

**How to apply**: <text>
```

If the vault has a project note (`$VAULT_DIR/projects/<slug>.md`), add
`- [[<file name without .md>]] <title>` under its `## Lessons` heading.

Finish with the file path, in one line.

## When a lesson keeps coming back

Search the folder for the same lesson first
(`grep -ril "<keyword>" "$LEARNINGS_DIR"`). If it is already there two or more
times, say so: a lesson that keeps coming back should become a hook or a test,
not a third note. See `hooks/bash-guard/` for an example.
