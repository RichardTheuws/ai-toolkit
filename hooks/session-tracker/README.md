# session-tracker

One line per Claude Code session in `~/.claude/session-log.jsonl`: project,
start, end, duration, and why it ended.

We use the log to chain sessions: at the start of a new session, the last entry
for this project plus `git log` tell Claude where we left off. That replaced the
"## Last session" notes we used to keep in memory, which went stale and cost
context in every session.

```json
{"project":"acme-shop","cwd":"/Users/you/code/acme-shop","session_id":"…","started":"2026-11-27T08:01:12Z","ended":"2026-11-27T09:40:55Z","duration_min":100,"reason":"exit"}
```

## Install

```bash
cp session-tracker.js ~/.claude/hooks/
```

In `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [{ "hooks": [{ "type": "command", "command": "node ~/.claude/hooks/session-tracker.js start", "timeout": 3 }] }],
    "SessionEnd":   [{ "hooks": [{ "type": "command", "command": "node ~/.claude/hooks/session-tracker.js end", "timeout": 1 }] }]
  }
}
```

Node 18+, no packages.

## Details

- Start times are kept per `session_id`, so parallel sessions don't overwrite each other.
- A resumed or compacted session keeps its original start time.
- The log keeps the last 500 sessions.
- It never fails the session; errors are swallowed.

## A mistake we made first

Our first version hung on the `Stop` event. `Stop` fires after every reply,
not at the end of a session, so the log filled with one line per turn.
`SessionEnd` is the right event.

## Make this better

What do you log per session, and what do you do with it? Tell us in the
[discussions](https://github.com/RichardTheuws/ai-toolkit/discussions).
