# Memory hygiene for Claude Code auto-memory

Claude Code keeps an auto-memory per project: a `MEMORY.md` index plus small topic files in `~/.claude/projects/<project>/memory/`. The index is read into context at the start of every session. The topic files are only opened when the index points to them and the task seems to need them.

That difference is the whole playbook. The index costs you context every session. The topic files are close to free until they are used. Without some discipline the index grows, starts to hold session notes and implementation details, and every session pays for all of it.

This is what works for us. It is not the only way. Tell us what you would change.

## The rules in short

1. **The index holds pointers, not content.** Every line answers one question: "where do I find X?"
2. **One fact per file.** A topic file covers one subject and can be read on its own.
3. **No session logs in memory.** Git history and your session tooling already know what happened and when.
4. **No version stamps in headings.** `## Payments (v2.3, March)` is a changelog fragment in disguise.
5. **In a monorepo, use a router plus one index per workstream.**
6. **Archive dormant workstreams.** Out of the index, not deleted.
7. **Measure what costs context, not what is easy to count.**

## 1. The index is a map

What belongs in `MEMORY.md`:

- Stable facts you need in every session (current version, main paths, deploy target), a few lines at most.
- One line per topic file, with a hook that says what makes that file different.
- A pointer to another project's memory if it matters every session.

What does not belong there:

- Explanations longer than one line.
- Lists of implementation details (ports, script names, config paths).
- Version history and changelog fragments.
- How-to guides and architecture descriptions.
- "Last session" or "Next session" sections.

A quick test before a line lands in the index: could a future session understand this line without knowing the rest of the project? If not, it belongs in a topic file.

### Index entry format

```markdown
- [Checkout gotchas](feedback_checkout_gotchas.md) — webhook retries double-book orders; idempotency key is the order id
```

One line, about 150 characters at most. The hook after the dash names the detail that makes this file the right one. Avoid hooks like "contains notes about checkout" or "important lessons". Leave out dates and status words; those live in the file.

Keep the headings flat and few. We use five: active projects, lessons and anti-patterns, technical reference, user preferences, and a short block of stable project facts. An ad-hoc heading for one subject ("## Payment service") is a sign that subject wants its own file.

## 2. One fact per file

File names use one of four prefixes:

| Prefix | Holds | Lives until |
|---|---|---|
| `feedback_` | Lessons, anti-patterns, "don't do this" | Permanent |
| `project_` | Status and decisions of a piece of work | The work is archived |
| `reference_` | Stable technical lookup | The source changes |
| `user_` | Preferences and communication style | Permanent |

After the prefix: snake_case, at most four words, specific enough that the name announces the content. `project_notes.md` says nothing. `project_checkout_v2.md` is wrong too: versions live inside the file, not in its name.

Each file starts with frontmatter:

```yaml
---
name: Checkout gotchas
description: Webhook retries double-book orders; use the order id as idempotency key
type: feedback
---
```

The `description` is the search key. Write it so the answer to "is this relevant to what I'm doing now?" is always yes or no, never maybe. Name the subject, not the occasion.

Do not merge small files just to get the count down. In a store that loads files lazily, many small files with sharp descriptions are a feature. Merge only when two files cover the same subject.

## 3. No session logs in memory

A "Last session" section grows every session: date, summary, next steps, blockers. After a few months it is the biggest part of the index, and almost none of it is still true.

Where that information already lives:

- When the last session was: your session tooling or hook log.
- What changed since then: `git log --since=<last session>`.
- What was decided: commit messages, or a `project_*.md` file if the decision is bigger than a commit message.
- Open items for ongoing work: an "Open items" section inside that project's file.

Memory is for what stays true. A session-start command can rebuild the rest from these sources.

## 4. Router plus workstream indexes (monorepos)

Claude Code keys memory on the **folder** you start the session in. Knowledge, though, belongs to a **project**, and a project often spans several folders or repos. Those two axes do not line up.

We learned this the hard way. One repo held five separate workstreams. The obvious fix, "give each workstream its own memory by starting sessions in its subfolder", had already been half done. It was the cause of the mess, not the cure: several subfolder memories with one file each, and which memory you got depended on where you happened to start. Splitting further along the folder axis made it worse.

What worked was to keep one memory for the repo and split by **how you need the knowledge**:

- `MEMORY.md` becomes a **router** of about 30 lines: one line per workstream pointing to its own `INDEX-<workstream>.md`, plus the few rules that apply everywhere.
- Each workstream index points to its own topic files.
- A session loads the router and one index. Topic files come in only when relevant.
- Subfolder memories stay thin: the hard facts of that checkout (paths, stack, deploy quirks) plus a pointer back up.

The result for us: the fixed context loaded per session went from about 15 KB to about 2 KB for the router alone, and about 5 KB for a session in the busiest workstream.

A caveat. Moving knowledge out of memory (for example into a notes vault) costs automatic recall. Memory files are found through their description; other notes have to be read on purpose. That is fine for decisions and history. Facts you must never get wrong stay in memory.

## 5. Archive dormant workstreams

A workstream with no activity for weeks does not need to load in every session. Move its files to `memory/archive/`, keep the frontmatter, add an `archived:` date, and remove its line from the router. Add a short README in the archive folder that says how to bring it back.

Activity is not always commits. One of our workstreams produces almost no commits and is still in active use; a commit counter would call it dormant. Decide per workstream, not per number.

## 6. Measure what costs context

We had an audit that turned red at more than 30 memory files. After the router change, fixed cost per session dropped by about 80 percent, and the audit got *worse*: five more index files. It also reported many "orphans" without an index entry, while a coverage check found none. They were all indexed, one level down.

An alarm that always goes off is no alarm. The fix was not to raise the threshold until it went quiet, but to measure the thing that hurts:

- **Measure the index, not the stock.** What loads every session is the cost. In a router setup, measure the largest index, not the total file count. The total stays as a safety net only.
- **Follow the index one level deep.** A file counts as indexed if `MEMORY.md` names it, or if a file that `MEMORY.md` names names it.
- **Keep the signals that catch real mess:** stale session files, version stamps in headings, long inline sections.

The thresholds we use for the index: green under 80 lines, orange from 80 to 150, red above 150. Topic files: lessons should stay short (a lesson is not a story), reference files may be longer.

## The tool

This repo has an audit script in [`scripts/memory-audit/`](../scripts/memory-audit/). It reads a project's memory, scores it green, orange or red, and lists concrete actions. It understands the router setup described above. See its README for usage.

## Before and after

A synthetic example. Before: a `MEMORY.md` for a repo with a shop, a newsletter and some internal tools.

```markdown
# acme-shop memory

## Last session (14 March)
- Worked on checkout webhooks, half done
- Next: test refunds, ask about tax rules
- Blocked on payment sandbox keys

## Payments (v2.3, March)
- Webhook handler in src/payments/webhook.ts, retries 5x with backoff
- Idempotency key = order id, otherwise retries double-book
- Sandbox on port 4010, live on 4000
- Refund flow still uses the old API, migrate later

## Newsletter
- Sends via a queue worker, cron at 06:00
- Template lives in templates/mail/, tables only, no CSS variables
- Unsubscribe link must be absolute

## Patterns & gotchas
- Docker build cache breaks on lockfile change
- Never run the seed script against production
- The CMS preview ignores trailing slashes
[...]
```

After: a router, with the details in their own files.

```markdown
# acme-shop memory (router)

Load only the index for the workstream this session is about.

| Workstream | Index |
|---|---|
| Shop and payments | [INDEX-shop.md](INDEX-shop.md) |
| Newsletter | [INDEX-newsletter.md](INDEX-newsletter.md) |
| Internal tools | dormant, see archive/ |

## Applies everywhere
- [Production safety](feedback_production_safety.md) — never seed production; deploy only via the script
- [Docker cache](feedback_docker_cache.md) — build cache breaks on lockfile change; rebuild without cache
```

And `INDEX-shop.md`:

```markdown
- [Checkout gotchas](feedback_checkout_gotchas.md) — webhook retries double-book; idempotency key is the order id
- [Payments setup](reference_payments_setup.md) — handler path, sandbox and live ports
- [Refund migration](project_refund_migration.md) — old API still in use; open items inside
```

The "Last session" block is gone; git and the session log hold that. The version stamp is gone. Each detail has one home.

## Make this better

This is how we work today, not a standard. If you handle memory differently, have a better threshold, or found a case where this advice goes wrong, open an issue or start a discussion at https://github.com/RichardTheuws/ai-toolkit/discussions.

---

*Written with Claude, checked by Richard.*
