---
description: Record an architecture decision (ADR) in your notes vault
argument-hint: "[project] [title]"
---

# /decision: record a decision

Write one Architecture Decision Record (Michael Nygard's format) as a markdown
file, so that months later "why did we do it this way?" has an answer.

## Where it goes

1. Folder: `$DECISIONS_DIR` if set, else `$VAULT_DIR/decisions`, else `~/vault/decisions`.
   Check with `echo "${DECISIONS_DIR:-${VAULT_DIR:-$HOME/vault}/decisions}"`. Create the folder if missing.
2. File name: `<YYYY-MM-DD>-<title-slug>.md` (today's date, lowercase slug, max ~60 chars).
3. If a file with that name exists, add `-2`, `-3`, ... Never overwrite.

## What to ask

Arguments: `$ARGUMENTS` (optional project slug, then title).

Fill in what you can from the conversation first. Then ask for what is still
missing, **all in one message**, numbered, short:

1. Project slug
2. Title (max ~10 words)
3. Status: `proposed` (default when unsure), `accepted`, `rejected`, `superseded`
4. Context: why is a decision needed now? (1-3 sentences)
5. Decision: what we do. Start with a verb. (1-2 sentences)
6. Alternatives: each option considered, and why it lost (one line each)
7. Consequences: what gets easier, harder, or is still unknown (2-3 sentences)
8. Supersedes: only for `superseded`, the file name of the decision it replaces

If the conversation already holds all of it, skip the questions and show the
draft for a yes/no instead.

## File format

```markdown
---
type: decision
project: <slug>
date: <YYYY-MM-DD>
status: <status>
title: "<title>"
supersedes: <file name or empty>
tags: [decision, <slug>]
---

# <title>

## Context
<context>

## Decision
<decision>

## Alternatives
- **<option>**: <why not>

## Consequences
<consequences>
```

If `supersedes` is set, also open that older file and set its `status:` to
`superseded`, with a line `Superseded by [[<new file name>]]` under the title.

If the vault has a note for the project (`$VAULT_DIR/projects/<slug>.md`), add a
line `- [[<file name without .md>]] <title>` under its `## Decisions` heading
(create the heading if missing).

Finish with the file path, in one line.

## When to use it

- A choice that will still matter later: X vs Y, a library, a deploy strategy, a scope change.
- A trade-off where the *why* is the valuable part.

Not for small, reversible choices that don't reach beyond one commit.
