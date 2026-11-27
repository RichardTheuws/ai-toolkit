# ai-toolkit

**English** · [Nederlands](README.nl.md)

Tools and notes from our daily work with Claude Code: hooks, commands, skills,
templates and playbooks. Each one started as a fix for something that went wrong
in our own work. We cleaned them up so you can use them, and we'd like to hear
what you would do differently. That is the point of publishing: together we get
better at this.

By Richard Theuws ([theuws.com](https://theuws.com)), built together with Claude.
**The guide**: [tools.theuws.com](https://tools.theuws.com/) explains how these tools work together, chapter by chapter, with screenshots.

## What's in here

### Hooks: rules Claude Code enforces, not just reads

| Tool | What it does |
|---|---|
| [bash-guard](hooks/bash-guard/) | Blocks three shell mistakes that kept coming back: `rsync --delete` that can wipe a `.env`, zsh `$var:x` traps, and tests chained to a push with `;` |
| [session-tracker](hooks/session-tracker/) | One log line per session (project, start, end, duration), so a new session knows where the last one stopped |
| [vault-context](hooks/vault-context/) | At session start, gives Claude the vault note of the project you are in |
| [compact-recovery](hooks/compact-recovery/) | After compaction, tells Claude the branch, uncommitted files and recent commits |
| [sound-cues](hooks/sound-cues/) | A sound when Claude is ready, working, failing or done, so you can look away from the terminal |

### Commands

| Command | What it does |
|---|---|
| [/session-start](commands/session-start.md) | Starts every session the same way: git, last session, memory check, vault note, open actions |
| [/decision](commands/decision.md) | Records an architecture decision as a dated markdown file |
| [/learning](commands/learning.md) | Records a lesson, and warns when the same lesson keeps coming back |

### Scripts

| Script | What it does |
|---|---|
| [memory-audit](scripts/memory-audit/) | Scores a project's auto-memory green / orange / red, and says what to fix |
| [leak-gate](scripts/leak-gate/) | Refuses to publish a folder with secrets, home paths, private IPs or names from your own denylist |

### Skills

| Skill | What it does |
|---|---|
| [li-check](skills/li-check/) | Quality check for LinkedIn drafts, with a hard transparency gate: it never helps hide AI use |

### Templates

| Template | What it is |
|---|---|
| [mcp-backend-wrapper](templates/mcp-backend-wrapper/) | Put your own app's API behind MCP as tools for Claude Code |

### Playbooks: how we work, and what bit us

| Playbook | Nederlands |
|---|---|
| [Working agreements with Claude Code](playbooks/working-agreements.md) | [Werkafspraken](playbooks/nl/werkafspraken.md) |
| [Memory hygiene](playbooks/memory-hygiene.md) | [Geheugenhygiëne](playbooks/nl/geheugenhygiene.md) |
| [An Obsidian vault as shared memory](playbooks/obsidian-as-shared-memory.md) | [Obsidian als gedeeld geheugen](playbooks/nl/obsidian-als-gedeeld-geheugen.md) |
| [A personal assistant that hands work to a coding agent](playbooks/personal-assistant.md) | [Persoonlijke assistent](playbooks/nl/persoonlijke-assistent.md) |
| [An integration standard for your own systems](playbooks/integration-standard.md) | [Koppelvlak-standaard](playbooks/nl/koppelvlak-standaard.md) |
| [Running Claude-built apps on a Mac mini](playbooks/running-on-a-mac-mini.md) | [Draaien op een Mac mini](playbooks/nl/draaien-op-een-mac-mini.md) |
| [One app for the whole house](playbooks/home-automation.md) | [Eén app voor het hele huis](playbooks/nl/home-automation.md) |

### In their own repositories

| Project | What it does |
|---|---|
| [video-studio](https://github.com/RichardTheuws/video-studio) | A Claude Code skill that makes a finished video from chat: edit footage or generate it, with an approval step before paid renders |
| [VOX](https://github.com/RichardTheuws/VOX-app) | macOS menu bar app that reads AI replies aloud from the terminal and editors, on-device |
| [FalconDebugger](https://github.com/RichardTheuws/FalconDebugger) | WordPress debugging plugin |

## Try it on a demo vault

`examples/demo-vault` is a tiny made-up vault (one project, two decisions, a lesson, two dev actions). Point `VAULT_DIR` at it to try the hooks and commands before using your own notes.

## How to use it

Nothing here needs installing as a whole. Each folder has its own README with a
copy-paste install, and almost everything runs on what macOS already has
(bash, Python 3, Node). Where a tool only works on macOS, or needs a paid API,
the README says so.

## What we left out, and why

Some of our tools are tied to one person's life, one house or one client: our
personal assistant, the home app, client work, our paid products. Those stay
private. Where the *pattern* is useful, it is in a playbook instead.

Everything here was copied into a fresh repository, never forked from a private
one, and every push goes through [leak-gate](scripts/leak-gate/).

## Make this better

- **Something broken or unclear?** [Open an issue](https://github.com/RichardTheuws/ai-toolkit/issues/new/choose).
- **You do it differently, or better?** Start a [discussion](https://github.com/RichardTheuws/ai-toolkit/discussions). We'd genuinely like to know.
- **A fix or a new rule with a test?** Pull requests welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT, see [LICENSE](LICENSE). `skills/li-check` is derived from Jake Schincariol's
MIT-licensed [linkedin-agent-skill](https://github.com/Jakeschincariol/linkedin-agent-skill)
and keeps its notice.
