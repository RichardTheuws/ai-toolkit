# An integration standard for your own systems

Once you run more than a handful of small apps, the seams between them start to break. Not the apps themselves: the places where one app hands something to another.

We learned this on a single day when we repaired the same kind of seam four times, in four repos:

| Where | What went wrong |
|---|---|
| The bookkeeping app | It matched incoming leads on email address and did not deduplicate on the sender's id. When the intake form delivered twice, we got duplicate notes and duplicate notifications. |
| Monitoring | The intake form counted failed jobs in its health endpoint. Nothing ever looked at that number. |
| The CRM and the intake form | Two vocabularies and two token systems for the same dashboard. |
| The intake form and our assistant | The form could send a notification, but nobody could reply, because its admin API sat behind a browser cookie. |

Four symptoms, one cause: every system solved the seam on its own. So we wrote it down once. Now each new seam bug becomes a rule in this document, not only a fix in one repo.

## The five rules

### 1. Server-to-server auth: a secret in a header, and off when the secret is missing

Between our own services, a shared secret in a header is enough, compared in constant time. Never a browser cookie for machine-to-machine calls.

The important half: **if the secret is not configured, the endpoint refuses with 503.** A misconfigured environment must never quietly accept data. We ended up with one small helper that has three outcomes: ok, 401 (wrong secret), 503 (no secret configured). That helper is our reference, not any single route.

On the open internet (payment providers, chat platforms, outside parties) we use **HMAC signing over the payload** instead. The content is then signed too, so a leaked secret alone is not enough. We first wrote the standard with only the header variant, and changed it after one of our own projects turned out to do it better.

### 2. Every ingest is idempotent on `(source, source_ref)`

`source` is the sending system. `source_ref` is the event's id in that system, for example a submission id. A unique index on that pair means a repeat delivery returns the same answer and causes no second note, invoice or notification.

This is the other side of rule 3. Whoever delivers at least once obliges the receiver to be idempotent. Make that agreement explicit.

One lesson from the fix: when the id was missing, our handler silently fell back to the old email match without deduplication. Harmless while the sender always sends an id, but a silent fallback is a future bug. Make it loud.

### 3. Delivery is at least once, with a retry ladder and a visible remainder

A job leaves the queue only when it succeeded. Retries follow a ladder: 30 seconds, 1 minute, 2 minutes and so on, up to an hour, eight attempts. After that the job is **visibly failed**, not gone. We would rather get something twice than miss it.

### 4. What failed is counted, and someone looks at it

A counter in `/api/health` is only a safety net if something reads it. Alert on **failed jobs > 0**, not on HTTP 200: an app can run fine while its queue is stuck. One monitor for all systems, with an interval that matches what a miss costs. A missed customer request is something we want to know within the hour, not the next day.

### 5. One channel for attention, in both directions

Everything that needs our attention goes through one channel (for us: our personal assistant in Telegram), in the same shape: an event, a message with buttons, and a **way back**. Replying by tap, text or voice turns into an answer in the source system. If the way back fails, the channel says so. Never fail silently, or you think you answered when you did not.

Mail is the fallback, not the main channel.

A refinement for products that run for several clients: the channel is a property of the *instance*, not of the code. Our own instance reports to our assistant. A client's instance keeps the client's own channel. Otherwise every client's notifications would run through our phone.

### And: one service per capability

Two copies of the same capability on one server (say, two speech-to-text installs) are allowed, but as a decision with a written reason. The default is one service per capability.

## Checklist for a new seam

- [ ] Secret in a header, constant-time compare, 503 when the env var is missing
- [ ] HMAC over the payload if the endpoint is reachable from the internet
- [ ] Unique `(source, source_ref)`; a repeat returns the same result with `duplicate: true`
- [ ] No silent fallback when `source_ref` is missing
- [ ] Sender uses an outbox with a retry ladder; failed jobs stay visible
- [ ] Failed count in the health endpoint, and a monitor that alerts on > 0
- [ ] Notifications go through the one channel, with a working way back
- [ ] Every action on the receiving side is idempotent, including "resolved" and "archive"

## A minimal sketch

An idempotent webhook receiver in Python with FastAPI and SQLite. It shows rules 1 and 2; your sender's outbox handles rule 3.

```python
import hmac, os, sqlite3, json
from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI()
db = sqlite3.connect("ingest.db", check_same_thread=False)
db.execute("""CREATE TABLE IF NOT EXISTS ingests (
  source TEXT NOT NULL, source_ref TEXT NOT NULL,
  result TEXT NOT NULL, PRIMARY KEY (source, source_ref))""")

def check_secret(given: str | None) -> None:
    expected = os.environ.get("INGEST_SECRET")
    if not expected:
        raise HTTPException(503, "ingest disabled: no secret configured")
    if not given or not hmac.compare_digest(given, expected):
        raise HTTPException(401, "bad secret")

@app.post("/api/ingest")
async def ingest(request: Request, x_ingest_secret: str | None = Header(None)):
    check_secret(x_ingest_secret)
    body = await request.json()
    source, ref = body.get("source"), body.get("id")
    if not source or not ref:
        raise HTTPException(422, "source and id are required")  # loud, no fallback

    row = db.execute("SELECT result FROM ingests WHERE source=? AND source_ref=?",
                     (source, ref)).fetchone()
    if row:
        return {**json.loads(row[0]), "duplicate": True}

    result = {"customer_id": create_note_and_notify(body)}  # your side effect
    try:
        db.execute("INSERT INTO ingests VALUES (?,?,?)", (source, ref, json.dumps(result)))
        db.commit()
    except sqlite3.IntegrityError:  # a parallel delivery won the race
        row = db.execute("SELECT result FROM ingests WHERE source=? AND source_ref=?",
                         (source, ref)).fetchone()
        return {**json.loads(row[0]), "duplicate": True}
    return {**result, "duplicate": False}
```

In production, claim the `(source, source_ref)` row *before* the side effect (or run both in one transaction), so two parallel deliveries cannot both notify. The sketch keeps it short.

## Applied: one feedback route from users into the backlog

We found that five of our apps each had their own feedback button. Each had its own storage and its own bot. None of them ended up in our backlog, and in none of them did the user ever hear that the report was solved. The feedback standard turns that into one route, built on the five rules above.

1. **Capture in the source.** The app's own database is the source. Four kinds: bug, question, idea and check-in. Context (page, version, role) is added automatically. Reports are scoped per organisation.
2. **Report through the one channel.** The app sends a `feedback` event from its own outbox with a retry ladder. For a question it includes a draft answer. Text that goes to the model or the chat platform contains no contact details: the person is a pseudonym. Links and token-like strings are stripped too, because whoever pastes a private link pastes a key.
3. **Decide with one tap.** Buttons: Send, Edit, Pick up, Archive. **An answer to a user only goes out after a human tap.** Every answer says it was drafted with AI.
4. **Into the backlog.** Only what we pick up becomes a dev-action in our notes repo, with `source: feedback` and `source_ref: <app>:<id>`. See the [personal assistant playbook](personal-assistant.md) for how those actions reach Claude Code.
5. **Close the loop.** Every 15 minutes the assistant checks which feedback actions are `done` and sends `resolved` to the app. The app marks the report solved and mails the user once.

The way back from the assistant to the app is one idempotent endpoint per app with an `action` field (`answer`, `picked_up`, `archive`, `resolved`) and its own secret header. A 404 counts as handled.

Connecting a new app is a table and an outbox in that app, one config line for the assistant, a project note so session start finds the actions, and a paragraph in the privacy statement that says who drafts the answer and how long reports are kept.

Lessons from the first builds:

- **Deliver reports on their own fast tick.** Riding along on a 5-minute cron meant a report arrived after 4 to 6 minutes. A separate 30-second tick brought it down to about half a minute. Never run two deliverers side by side, or messages arrive twice.
- **Quote config values that contain commas.** One unquoted line was skipped with only a note in the error log; the report still reached the chat, but without buttons.
- **Keep the button payload small.** Telegram limits callback data to 64 bytes, so we keep source names short.

## Make this better

These rules came from our own bugs, so they cover our blind spots only as far as we have hit them. If you have a seam rule we are missing, or a cleaner way to do one of these, open an issue or start a thread at https://github.com/RichardTheuws/ai-toolkit/discussions.

---

*Written with Claude, checked by Richard.*
