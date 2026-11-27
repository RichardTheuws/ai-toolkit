# sound-cues

A Claude Code hook that plays a short sound when Claude is ready, gets your
prompt, edits a file, runs a command, hits an error, asks for permission or
finishes. You can look away from the terminal and still know when it needs you.

Packs are swappable, a pack can hold several variants per moment (picked at
random), and each terminal tab can use its own pack, so you can tell two
sessions apart by ear.

It ships with one pack, `system-default`, which uses the sounds already on every
Mac. **Bring your own sounds** for anything else; only use audio you have the
rights to (see [packs/README.md](packs/README.md)).

| Moment | Hook event | Sound | system-default |
|---|---|---|---|
| Session starts | `SessionStart` | `ready` | Glass |
| You send a prompt | `UserPromptSubmit` | `acknowledge` | Pop |
| File edited | `PostToolUse` (Edit, Write, MultiEdit, NotebookEdit) | `work` | Tink |
| Shell command | `PostToolUse` (Bash) | `command` | Morse |
| Tool failed | `PostToolUseFailure` | `error` | Basso |
| Claude is done | `Stop` | `done` | Hero |
| Asks permission | `Notification` (`permission_prompt`) | `alert` | Funk |
| Waiting for you | `Notification` (`idle_prompt`) | `idle` | Submarine |

## Install

```bash
mkdir -p ~/.claude/hooks
cp -R sound-cues ~/.claude/hooks/
```

Add to `~/.claude/settings.json` (next to any hooks you already have):

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "node ~/.claude/hooks/sound-cues/sound-cues.js", "timeout": 5 }] }
    ],
    "UserPromptSubmit": [
      { "hooks": [{ "type": "command", "command": "node ~/.claude/hooks/sound-cues/sound-cues.js", "timeout": 5 }] }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash|Edit|Write|MultiEdit|NotebookEdit",
        "hooks": [{ "type": "command", "command": "node ~/.claude/hooks/sound-cues/sound-cues.js", "timeout": 5 }]
      }
    ],
    "PostToolUseFailure": [
      { "hooks": [{ "type": "command", "command": "node ~/.claude/hooks/sound-cues/sound-cues.js", "timeout": 5 }] }
    ],
    "Stop": [
      { "hooks": [{ "type": "command", "command": "node ~/.claude/hooks/sound-cues/sound-cues.js", "timeout": 5 }] }
    ],
    "Notification": [
      {
        "matcher": "permission_prompt|idle_prompt",
        "hooks": [{ "type": "command", "command": "node ~/.claude/hooks/sound-cues/sound-cues.js", "timeout": 5 }]
      }
    ]
  }
}
```

Leave out the events you don't want to hear. Keep the `~` outside quotes so the
shell expands it. Requires Node.js 18+, no packages.

Check it works, then restart Claude Code:

```bash
echo '{"hook_event_name":"Stop"}' | node ~/.claude/hooks/sound-cues/sound-cues.js
```

A shorter command is handy:

```bash
alias sound-cues='node ~/.claude/hooks/sound-cues/sound-cues-cli.js'
```

## Switching packs

```bash
sound-cues list             # installed packs
sound-cues use my-pack      # switch globally
sound-cues test             # hear every sound of the current pack
sound-cues test done        # just one
sound-cues volume 0.3
sound-cues off              # mute everything; `on` to undo
sound-cues event PostToolUse off   # mute one event
sound-cues status
```

Settings live in `config.json` next to the script; it is created the first time
you change something. Without it, the defaults apply: all events on, volume 0.5,
and a cooldown so a burst of edits doesn't turn into a drum solo (300 ms between
any repeat, 2 s for edits and commands, 1 s for errors).

## A different pack per terminal

```bash
sound-cues session my-pack  # only this tab, for 24 hours
sound-cues session-clear
```

This works in terminals that expose a tab id: iTerm2, Terminal.app, Windows
Terminal, kitty and WezTerm. Anywhere else, set an environment variable before
starting Claude Code:

```bash
SOUND_CUES_PACK=my-pack claude
```

Order of precedence: tab override, then `SOUND_CUES_PACK`, then `config.json`.

## Making your own pack

A pack is a folder with a `pack.json` that maps sound names to files. The format,
sound names and tips for making recordings are in
[packs/README.md](packs/README.md). Short version:

```json
{
  "name": "My pack",
  "sounds": {
    "ready": "hello.aiff",
    "done": ["done-1.aiff", "done-2.aiff"],
    "error": "oops.aiff"
  }
}
```

```bash
sound-cues add ./my-pack && sound-cues use my-pack
```

Bring your own sounds, and only use audio you have the rights to.

## Test

```bash
node --test   # in this folder; plays nothing (SOUND_CUES_DRY_RUN=1)
```

`SOUND_CUES_DRY_RUN=1` also works for the hook itself: it prints the file it
would play to stderr. `SOUND_CUES_HOME` points the hook and CLI at another
folder for `config.json` and `packs/`.

## Known limits

- `system-default` only works on macOS; the files are in `/System/Library/Sounds`.
- Linux: plays through `paplay` (or `aplay` for `.wav`) if installed, but you need
  to make a pack first, for example pointing at `/usr/share/sounds/freedesktop/stereo/`.
  Tested on macOS only.
- Windows: no player, so it stays silent (and harmless).
- The hook never blocks or fails a session: every error is swallowed, it exits 0,
  and stdin reading gives up after 1.5 s. The flip side is that a broken pack is
  silent rather than loud about it. Use `sound-cues test` to find out why.
- Cooldowns are per event, not per sound, and are shared by all open sessions.

## Make this better

Got a better default mapping, a Linux setup that works, or a terminal whose tab id
we should read? Open an issue or start a
[discussion](https://github.com/RichardTheuws/ai-toolkit/discussions).
