# A personal assistant that hands work to a coding agent

This playbook describes two things we run every day:

1. **Our personal assistant**: a small service on an always-on machine at home that we talk to through Telegram. It reads mail, drafts replies, transcribes voice memos and knows our notes.
2. **The dev-action loop**: how that assistant hands a code change to Claude Code without ever touching code itself.

The assistant's code is not published. It is tied to one person's life and work, and most of it is glue to private accounts. The architecture is the useful part, so that is what we share. Take what fits, and tell us what you would do differently.

## Part 1: the architecture

### One service, several front-ends

The core is one Python service: FastAPI plus the Claude Agent SDK, running as a background service with automatic restart. It has a small number of endpoints, mainly `POST /ask` and `POST /transcribe` for voice. It binds to localhost and is only reachable over a private network (a mesh VPN), with a shared-secret header on top. There are no open ports to the internet.

We chose the Agent SDK over a plain completion call because the assistant is an agent with tools, and a warm process answers in seconds.

Telegram is the main front-end. A desktop voice front-end talks to the same service. **One canonical channel** is a rule for us: when something new needs our attention, we add it to the one assistant. We never build a second bot next to it.

### Telegram: long polling, not webhooks

The Telegram bot runs inside the service as a background task. On startup it calls `deleteWebhook` and then polls `getUpdates`, for both messages and button taps.

Polling and webhooks are mutually exclusive in Telegram. If anything calls `setWebhook` on the same bot token, polling stops and the whole channel goes quiet. We nearly did exactly that: we were about to switch on an automation workflow with a Telegram webhook trigger for a new notification. It would have broken the assistant and duplicated something it already did. It happened because the assistant only existed on the server and could not be found from any repo. Since then it has a reference note that every project can find.

Two more rules from the same corner:

- Never run two pollers on one token. Telegram answers with HTTP 409.
- A chat guard: the bot only accepts messages from one known chat.

Voice notes are transcribed locally (ffmpeg plus whisper.cpp). We tried local models for the chat itself and dropped them; the quality gap was too large. Cloud model plus a spending cap won.

### Tools

The assistant gets its tools through MCP servers, with a strict allowlist. No shell, no file read or write, only the tools we intend:

| Tool | How |
|---|---|
| Mail (several accounts) | one mail MCP per account, each with its own credentials |
| Calendar | same pattern |
| Tasks and admin | a small MCP wrapper around an existing backend |
| Obsidian vault, read | a read-only git clone on the server that pulls every 15 minutes |
| Vault capture, write | a tool that may only add new files to one inbox folder |
| Mail agents | an existing automation tool classifies incoming mail and prepares draft replies |

Two habits made this cheap. We **wrap existing systems instead of rebuilding them**: the admin wrapper was about fifty lines. And the vault, our second brain, is fed by Claude Code sessions, so the assistant knows what was decided in each project without anyone telling it.

### Security: the part that matters most

Each tool has a tier:

| Tier | Meaning | Rule |
|---|---|---|
| 0 | read | free |
| 1 | draft | free, this is the default for mail |
| 2 | send, create calendar items | needs explicit confirmation |
| 3 | delete, filters | closed |

**Confirmation is enforced by the transport layer, not the model.** The model can only propose a tier-2 action. The bot shows confirm and cancel buttons. Only after a tap does the same session run again with a `confirmed` flag, and only that flag unlocks tier-2 tools. The model cannot raise its own permissions, also not under prompt injection.

People type "yes" instead of tapping the button. An exact-match word list in the transport layer catches that, without giving the model any say in it.

We tested this with planted mails that contained hidden instructions, including one where we ourselves asked the assistant to "do what that mail says". It refused, and tier 2 stayed closed. As a second floor, the OAuth scopes are so narrow that deleting mail is not possible at all.

The rest of the safety model:

- **Drafts only by default.** Mail agents prepare drafts. Sending is a human tap.
- **A spending cap.** Each component has its own API key with a monthly spend limit as a hard circuit breaker. Every call is logged with its cost, and the assistant can report its own daily cost.
- **Append-only audit log.** Every action goes to a JSONL file, rotated daily, with a retention period.
- **Credential isolation.** Separate keys per component, file mode 600, never in git.

### The most expensive lessons

1. Put confirmation in the transport layer. Anything in the prompt is theatre under injection.
2. Agent SDK `resume` keeps the old system prompt. We store a hash of the prompt with each session and start a fresh session when it changes, so every behaviour change invalidates running sessions.
3. Google OAuth apps in "Testing" mode lose their tokens after seven days. Set the app to production, also for personal use.
4. Ask the constraints first. "It must work on my phone" changed the whole design from a laptop tool to a shared service with several front-ends.

## Part 2: the dev-action loop

The assistant cannot change code or deploy. That is on purpose. But we often think of an improvement while away from the laptop, and we want it to land where code work actually happens: in a Claude Code session in the right repo.

### How it works

1. **The assistant writes one file.** It has one tool for this: `add_dev_action(project, title, spec)`. It writes a new markdown file to the vault at `dev-actions/<project>/<date>-<slug>.md`, with `status: open` in the frontmatter. The tool is append-only: it never edits or deletes an existing file. A prompt-injected mail can at worst add a suggestion, and a human reads every suggestion before anything is built.
2. **Session start lists open actions.** When Claude Code starts a session in that project, our `/session-start` command looks in the project's folder, reads every file with `status: open`, and shows title, one-line spec and path in the opening banner, with an offer to pick them up.
3. **Claude Code implements.** In the dev environment, with tests, and it shows the diff before deploy. That is the same approval gate as for any other change.
4. **Closing.** After implementation and deploy, Claude Code edits the file: `status: done`, `done: <date>`, `commit: <sha>`. It commits that in the vault repo. Next session, the action is gone from the banner.

Claude Code may edit vault files. The assistant may not. That split is the whole safety argument.

The `<project>` folder name matches the project's note in the vault, and that note has a `repo:` field. That is how a session in a repo finds its actions. One lesson: never guess a slug and then report "no actions". When the slug lookup finds nothing, we also search the dev-actions folder for the repo's folder name. Guessing once hid three open actions from us.

### Actions that wait

An open action can be correct and still not be due. Without a way to say that, every session start repeats it, and you start ignoring the banner. Two optional fields fix this:

- `not_before: <date>` hides the action until that date.
- `wait_for: <event>` hides it until something happens that has no date, for example "the new staging server is live".

Waiting actions are not listed one by one. The banner shows one line: "3 waiting (next: 2026-12-01 <title>)". Each session briefly checks every `wait_for` against the git log and the vault. When the event has happened, the field is removed and the action shows up normally. Otherwise it would stay invisible forever.

### An overview across projects

A scheduled script scans all `dev-actions/<project>/*.md` for `status: open` and overwrites one overview note in the vault. A derived view: idempotent, safe to run as often as you like.

### Example action file

A synthetic example. The project, the dates and the details are made up.

```markdown
---
type: dev-action
project: invoice-app
status: open
source: assistant
created: 2026-11-20T08:42:00+01:00
not_before: 2026-11-24
---

# Show the due date on the invoice list

## Spec
In the invoice list, add a "Due" column next to "Amount". Overdue
invoices get the existing warning colour. Sort by due date when the
column header is clicked.

## Why
Asked from the phone while checking which invoices to chase.

## Done when
- Column visible on desktop and mobile
- Test for the overdue state
- Diff shown before deploy
```

After the work, Claude Code changes the frontmatter to:

```yaml
status: done
done: 2026-11-25
commit: 3f9c2ab
```

### Feedback from users uses the same folder

A user report that we pick up in Telegram becomes a dev-action with `source: feedback` and a `source_ref` back to the report. When it goes to `done`, the user hears once that it is solved. An action we will not build gets `status: dropped` with one line of why. The full route is in the [integration standard](integration-standard.md).

## Make this better

This is what works for us, not the only way. If you run something similar and solved a part differently, or see a hole in the security model, we would like to hear it. Open an issue or start a thread at https://github.com/RichardTheuws/ai-toolkit/discussions.

---

*Written with Claude, checked by Richard.*
