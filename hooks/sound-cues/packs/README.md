# Pack format

A pack is a folder in `packs/` with a `pack.json` and, usually, some audio files.
The folder name is the pack id you pass to `use`, `session` or `SOUND_CUES_PACK`
(letters, digits, `.`, `-`, `_`).

```
packs/
  my-pack/
    pack.json
    hello.aiff
    done-1.aiff
    done-2.aiff
    oops.aiff
```

## pack.json

```json
{
  "name": "My pack",
  "description": "Short recordings of my own voice",
  "sounds": {
    "ready": "hello.aiff",
    "done": ["done-1.aiff", "done-2.aiff"],
    "error": "oops.aiff"
  }
}
```

| Field | Required | Meaning |
|---|---|---|
| `name` | no | Display name in `list` and `test` |
| `description` | no | One line for `list` |
| `sounds` | yes | Sound name to a file, or to a list of files |

Each value in `sounds` is either:

- **a file name**: always that file, or
- **a list of file names**: one is picked at random each time, so it gets old less fast.

Relative paths are resolved from the pack folder. Absolute paths work too; that is
how `system-default` points at `/System/Library/Sounds/`. Files that don't exist are
skipped. If no file for a sound exists, that moment stays silent.

## Sound names

| Sound | When it plays |
|---|---|
| `ready` | Session starts (`SessionStart`) |
| `acknowledge` | You send a prompt (`UserPromptSubmit`) |
| `work` | Claude edits a file (`PostToolUse` with Edit, Write, MultiEdit, NotebookEdit) |
| `command` | Claude runs a shell command (`PostToolUse` with Bash) |
| `error` | A tool call fails (`PostToolUseFailure`) |
| `done` | Claude finishes its turn (`Stop`) |
| `alert` | Claude asks for permission (`Notification`, `permission_prompt`) |
| `idle` | Claude is waiting for you (`Notification`, `idle_prompt`) |

You don't have to fill all eight. Unmapped sounds are silent; there is no fallback
to another pack.

## File types

Anything your player handles. On macOS that is `afplay`: AIFF, WAV, MP3, M4A, CAF.
On Linux, `.wav` goes to `aplay` and everything else to `paplay` (PulseAudio or
PipeWire), so OGG/OGA and FLAC work there too.

Keep sounds short (under a second or two). A long clip overlaps with the next one.

## Making sounds

Only use audio you have the rights to: your own recordings, or files with a license
that allows it. Clips ripped from games, films or TV shows are not fine just because
they are on a soundboard site.

Quick ways to make your own:

```bash
# macOS text-to-speech
say -o done-1.aiff "Done"
say -o oops.aiff "That failed"

# Record yourself (macOS, needs: brew install sox)
rec -c 1 hello.wav trim 0 1.5

# Linux: the freedesktop theme that ships with most desktops
ls /usr/share/sounds/freedesktop/stereo/
```

Then add the pack:

```bash
node ~/.claude/hooks/sound-cues/sound-cues-cli.js add ./my-pack
node ~/.claude/hooks/sound-cues/sound-cues-cli.js use my-pack
node ~/.claude/hooks/sound-cues/sound-cues-cli.js test
```

Or create the folder directly in `~/.claude/hooks/sound-cues/packs/`; `add` only copies.
