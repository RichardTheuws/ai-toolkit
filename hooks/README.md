# Hooks

Claude Code [hooks](https://code.claude.com/docs/en/hooks) run your own scripts on
events like "before a shell command" or "session start". A written rule in
CLAUDE.md is a suggestion; a hook is enforced. We turn a lesson into a hook when
it keeps coming back.

| Hook | Event | What it does |
|---|---|---|
| [bash-guard](bash-guard/) | PreToolUse (Bash) | Blocks three recurring shell mistakes |
| [session-tracker](session-tracker/) | SessionStart + SessionEnd | One log line per session |
| [compact-recovery](compact-recovery/) | SessionStart (compact) | Restores branch and git state after compaction |
| [sound-cues](sound-cues/) | several | A sound per state, so you can look away |
