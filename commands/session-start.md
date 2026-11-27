---
description: Start a work session with context - git state, last session, memory health, vault note, open actions
---

# /session-start

Load what this session needs to know, show it in one short banner, and then
wait. The user's next message is the goal of the session; don't ask for one.

Run the steps below. Skip a step silently when its tool or folder doesn't exist.
Keep the banner short: show only what deserves attention.

## 1. Git

```bash
git fetch origin 2>/dev/null
git status --short --branch
git log --oneline -5
```

Report: branch, clean or dirty (number of files), ahead/behind the remote.
Uncommitted changes: mention them, don't offer to commit them.

## 2. Where the last session stopped

If `~/.claude/session-log.jsonl` exists (written by `hooks/session-tracker`),
show the last entry for this project folder: when it ended and how long it took.

```bash
grep "\"project\":\"$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")\"" ~/.claude/session-log.jsonl 2>/dev/null | tail -1
```

Together with `git log` this is the session history. Don't look for
"## Last session" notes in memory; they don't belong there.

## 3. Memory health

Run the audit from the **git root**, because auto-memory is keyed on the folder
Claude Code was started in:

```bash
~/.claude/scripts/memory-audit.sh --quiet --project-dir "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

- GREEN: show nothing.
- ORANGE: one line with the first reason.
- RED: a clear warning above the banner with all reasons, and point to
  `playbooks/memory-hygiene` in the guide.

## 4. The project note

If the `vault-context` hook ran, the project note is already in context: use
it, don't read it again. Otherwise look for `$VAULT_DIR/projects/<repo-name>.md`
and read only its frontmatter and current-state section.

## 5. Open actions

Work that someone (your assistant, a colleague, you on your phone) filed for
this project, as files in `$VAULT_DIR/dev-actions/<repo-name>/`:

```bash
grep -l "^status: open" "${VAULT_DIR:-$HOME/vault}"/dev-actions/"$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")"/*.md 2>/dev/null
```

For each open action read the title and the first lines of the spec.

- An action with `not_before:` after today, or with `wait_for:`, is not due:
  don't list it, count it in one line ("2 waiting, next: 3 Dec <title>").
- Due actions: list them with a one-line summary and the file path, and offer
  to pick them up (implement with tests, show the diff before deploying).
- After an action is implemented and deployed, set `status: done`,
  `done: <date>`, `commit: <sha>` in its frontmatter.

## 6. Banner

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SESSION STARTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project: <name> | v<VERSION if present> | <branch> | <clean / N dirty> | <ahead/behind>
Last session: <date>, <duration>
Memory: <only if not green>

<due actions, if any, with the offer to pick them up>
<waiting actions, one line>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Then stop and wait for the user.
