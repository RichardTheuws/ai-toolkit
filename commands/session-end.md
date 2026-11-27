---
description: End a work session cleanly - tests, commit, close actions, memory check, at most two notes worth keeping
argument-hint: "[optional note for the next session]"
---

# /session-end

Leave the project so the next session can start from facts, not from memory.
Do the routine parts without asking. Ask once, at the end, only about what is
worth keeping.

Optional argument: `$ARGUMENTS` is a note from the user for the next session
(a blocker, a reminder). Don't ask for one when it is empty.

## 1. What happened in this session

```bash
git status --short
git log --oneline --since="$(tail -1 ~/.claude/session-log.jsonl 2>/dev/null | sed -n 's/.*"started":"\([^"]*\)".*/\1/p')" 2>/dev/null | head -20
git diff --stat
```

From this and the conversation, list in two to five lines what changed.

## 2. Leftovers

Look at the changed files for things that should not be committed: debug prints,
commented-out code you added, temporary files, new `TODO`s without context.
Report them; don't fix them silently.

Stop background processes **this session** started (dev servers, watchers) unless
the user wants them running. Never touch processes you didn't start.

## 3. Tests are the gate

If code changed: run the project's linter, type check and tests (whatever the
project uses: `npm test`, `pytest`, a `Makefile` target). Red means stop: report
the failure and don't commit broken work. Run tests and commit as separate steps,
never chained with `;`.

## 4. Commit and push

- If the project keeps a `VERSION` file and a `CHANGELOG.md`, bump the version
  (feat = minor, fix/docs/chore = patch) and add a changelog entry.
- Commit with a conventional message (`feat:`, `fix:`, `docs:`, `chore:`, ...),
  one subject line under about 50 characters.
- Push. If the project deploys after a push, follow its deploy script or
  `DEPLOY.md` literally and confirm the live version before calling it done.

## 5. Close the actions you finished

For each dev action in `$VAULT_DIR/dev-actions/<repo-name>/` that this session
implemented and shipped, set in its frontmatter:

```yaml
status: done
done: <YYYY-MM-DD>
commit: <short sha>
```

An action that turned out to wait for something gets `wait_for: <what>` instead,
so `/session-start` stops listing it.

## 6. Memory check

```bash
~/.claude/scripts/memory-audit.sh --quiet --project-dir "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

- Green: nothing to do.
- Orange or red: fix what the audit lists if it is quick and clearly right
  (remove a session section, link or delete an orphan). Otherwise report it.

Never write a "last session" note into memory. The session log and git hold that.

## 7. Worth keeping? At most two proposals

Look back over the session for a **decision** (a choice between options that will
matter later) or a **lesson** (something that went wrong or surprised, with a root
cause). Be strict: when in doubt, propose nothing.

Before proposing, search the vault for the same thing:

```bash
grep -ril "<two or three keywords>" "${VAULT_DIR:-$HOME/vault}/decisions" "${VAULT_DIR:-$HOME/vault}/learnings" 2>/dev/null
```

Propose at most two, in **one** message, each with a one-line summary and a
choice: A) record it (`/decision` or `/learning` format), B) add it to the
existing note it duplicates, C) skip. Mark one option as recommended.
If a lesson already exists twice, say so: it should become a hook or a test.

If the user gave a note as argument, add it to today's daily note
(`$VAULT_DIR/daily/<YYYY-MM-DD>.md`), under the project name.

## 8. Code review: advice only

Never start a code review yourself, also not through a subagent. If the session
changed something risky (auth, payments, migrations, infrastructure, a large
diff), say in one line that a review is advisable and why. The user decides.

## 9. Close

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SESSION ENDED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Done: <two to five lines>
Committed: <sha> <subject> | pushed | <version>
Actions closed: <titles>   Memory: <verdict>
Kept: <decision/lesson titles, or none>
Next: <the most useful next step, one line>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

The `session-tracker` hook writes the session log line when Claude Code exits;
`/session-start` reads it next time.
