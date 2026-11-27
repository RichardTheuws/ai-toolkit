# Working agreements with Claude Code

These are the working agreements we settled on between ourselves and Claude Code. None of them is clever. Most exist because something went wrong, or kept going wrong. For each: the rule, the reason, and how we enforce it.

They fit how we work: one developer, many small projects, long sessions, a lot of subagents. Yours will differ.

## 1. Hard verdicts: PASS, FAIL or KILL

**The rule.** Every judgment the agent gives lands on PASS, FAIL or KILL. Not "borderline", not "leans FAIL", not "revise". If it cannot decide yet, it names the one measurement that would decide, goes and gets it, and then gives the verdict.

**Why.** A soft verdict hands the decision back without the information to make it. "Marginal" usually means "I haven't measured the thing that matters". Naming that measurement turns a vague answer into a small task. KILL is a real option, not a consolation prize.

**How we enforce it.** A short section in the global `CLAUDE.md`.

## 2. Recommend, don't hand out a menu

**The rule.** The agent never ends a block of work with "which direction do you want?". It gives:

- the recommendation;
- why this one, grounded in evidence or the goal;
- why not each alternative, one line each;
- the implications;
- the next step and how we will know it worked;
- "I'll start on this unless you veto."

**Why.** Options without a preference push the thinking back to the person who asked. The one-line rejection of each alternative is what makes it a recommendation rather than a menu with a label on one item. "Unless you veto" instead of a yes/no question keeps work moving; we only speak up when we disagree.

**How we enforce it.** In `CLAUDE.md`, as part of a short communication-style section.

## 3. Facts yourself, preferences ask

**The rule.** If the doubt is factual, the agent resolves it itself, with code, data, logs or notes. It only asks us about real preferences (risk tolerance, scope, policy, timing) or before an irreversible or destructive step. When it does ask, it asks all open questions at once, in one message, as A/B/C choices with one marked **(Recommended)** and at most two sentences per option.

**Why.** Questions about facts the agent could look up cost attention. Questions dripped one at a time are worse. A/B/C with a recommendation takes ten seconds to answer.

**How we enforce it.** In `CLAUDE.md`. Routine actions with an obvious "yes" (deploy after commit and push, cleanup) are listed as things it just does; destructive ones (data loss, production migrations, force pushes) as things it always asks about first.

## 4. No effort-framing

**The rule.** The agent never argues for or against an option by how much work it is. No "this is a lot of work", no "about ten hours", no "too heavy". It reasons from the goal backwards. It only estimates effort when we ask, or when it matters for ordering work.

**Why.** For an agent, the cost of building something is not the constraint it used to be. "That's a big job" pulls choices towards the smaller option, even when the bigger one is right for the project. Effort is a scheduling question, not an argument.

**How we enforce it.** One paragraph in `CLAUDE.md`.

## 5. Subagents return decisions, not questions

**The rule.** A subagent never ends its output with "open questions for the user". Choice points come back as decisions with a recommendation per point. The orchestrating session turns any that need a human into one A/B/C message in the chat. Each subagent also leaves a short, dated "yield" note: what it found, what it recommends, which files it touched, how confident it is. A human decides what, if anything, from those notes is kept.

**Why.** During a run of four parallel subagents, one returned a document ending in five open questions. A subagent has no channel back to the user, but that is no reason to park questions in a document; a document ending in "what do you want?" has to be mined by hand. The yield notes serve as an audit trail and as input for the end-of-session review. We chose no automatic promotion: yields are raw material, and a person filters.

**How we enforce it.** A standard line in every subagent prompt: return choice points as decisions with a recommendation, never as open questions for the end user. A short contract document defines the yield format (a few required frontmatter fields, five to ten lines of body, a dated filename per agent). The end-of-session command scans fresh yields and proposes at most two things to keep.

## 6. A lesson that keeps coming back becomes a hook

**The rule.** When the same mistake comes back a second time while a written lesson about it already exists, we stop extending the lesson and build a check that runs at the moment of the mistake: a `PreToolUse` hook, or a fixed script that contains the recipe.

**Why.** One deploy mistake with `rsync --delete` had been written down as a lesson six times in a few months. A zsh pitfall (`$var:latest`, where zsh reads `:l` as a modifier) was written five times in a deploy document. Both happened again anyway: a production `.env` was wiped and a rollback tag failed. A lesson gets read when it looks relevant, but after a context summary the agent rebuilds a command from memory, and the lesson is not in view. Text is advice; a hook is a gate.

**How we enforce it.** The shell guard in [`hooks/bash-guard/`](../hooks/bash-guard/) blocks exactly the three mistakes that came back: `rsync --delete` without `.env` protection or with options in a string variable, `$var:latest`-style modifiers, and "test, then commit" chained with `;` (so the commit runs even when the tests fail). Before adding a rule, we replay it against the Bash history in past session transcripts to see how many false alarms it would give.

**The counter-lesson: gates can overshoot.** We also built a review gate: a `Stop` hook that blocked the end of a turn until risky changes (migrations, auth, payments, deploy scripts, large diffs) had been code-reviewed. The trigger was real: a set of server-move scripts had run for two days without review, and the first review found ten bugs. But the gate fired far too often: 147 reviews in six days, against 8 the week before. And a `Stop` hook combined with a review skill that runs in the background produced a loop: the turn ended while the review was still running, the hook saw "no review" and blocked again, and sometimes the model started a second one. We switched it off for one review per session. A later count still showed 91 reviews in three and a half days, and the follow-up cost one and a half times the review itself, because the whole list was fixed without weighing and then reviewed again.

So now the agent never starts a review on its own. The end-of-session command only advises one, and we start it ourselves with a fixed recipe: one repo, only finished work, a level chosen by diff size and sensitivity, every finding weighed first (now / backlog / drop), a failing test before every fix, backlog items collected in one follow-up note, and no second review of the fixes. The tests are the check.

What we took from both: a hook suits a mistake that is cheap to detect and expensive to make, not a judgment call that should happen sometimes. And a `Stop` hook that triggers background work has to know that work is still running.

## 7. Clean up CLAUDE.md now and then

**The rule.** Periodically remove instructions that compensated for weaknesses of older models. Keep the core rules, the ones that describe the goal and the boundaries, unchanged. Archive skills and commands nobody uses, based on actual usage, not on feeling. Keep `CLAUDE.md` under version control.

**Why.** Our global `CLAUDE.md` had grown to 369 lines: tool-usage rules, search protocols, stale status notes, and autonomy rules that contradicted each other and were already steering behaviour. We rejected "delete everything and see what breaks": the core rules would go, and the damage shows up later. After cleanup: 214 lines. Fifteen commands and thirteen skills were archived (reversibly), chosen from eleven months of command history.

**How we enforce it.** The file lives in a git repo, symlinked from `~/.claude/`, with its own changelog. Transcripts are kept long enough to measure usage next time.

## 8. Be transparent about AI

**The rule.** We never hide that we use AI. No tooling, prompts or copy meant to make text "sound less like AI", be "undetectable", or get past detectors. Cleaning up text is fine as a matter of writing quality: clearer, more specific, in our own voice. "Was this made with AI?" always gets an honest answer. Messages to other people use only what they shared publicly or told us directly; never invented familiarity, numbers or results.

**Why.** It is an ethical line, not a style choice. Writing help that exists to deceive the reader is not something we build or use.

**How we enforce it.** A short section in `CLAUDE.md`, and a transparency gate in [`skills/li-check/`](../skills/li-check/): every draft for outside readers goes through it, and it fails on anything that denies AI use, open placeholders, or internal notes leaking into public text. The note at the bottom of this playbook follows the same rule.

## 9. Test before you claim it works; done means verified in production

**The rule.** The agent runs linters, type checks, existing tests and edge cases before saying something works. New features get tests in the same session, unasked. Test against production limits (URL length, batch sizes, real data volumes), not only fixtures. A task is finished when it is deployed and the live version (health endpoint or `VERSION`) shows the new one. If tests fail after a deploy, fix and redeploy.

**Why.** "Code done" and "works for the user" are different states. Caches, a deploy that did not land, and fixtures much smaller than real data all sit in between.

**How we enforce it.** In `CLAUDE.md`, plus deploy commands taken literally from a deploy script or `DEPLOY.md`, never from memory, and the shell guard from agreement 6.

## Copy this into your own CLAUDE.md

```markdown
## Working agreements
- Verdicts: every judgment ends in PASS / FAIL / KILL. Never "borderline". If you can't
  decide, name the one measurement that decides it, get it, then decide.
- Recommend, don't list options: recommendation, why this one, why not each alternative
  (one line each), implications, next step + success criterion, "I'll start unless you veto".
- Resolve factual doubt yourself (code, data, logs). Ask only about real preferences or
  before irreversible steps; ask all questions at once, as A/B/C with one (Recommended).
- Never argue for or against an option by how much work it is. Reason from the goal.
- Subagents: return choice points as decisions with a recommendation, never as open
  questions for the user. Leave a short dated note: findings, recommendation, files, confidence.
- A mistake that comes back despite a written lesson gets a hook or a script, not a longer lesson.
- Never hide AI use. No "undetectable" or detector-evading text. "Was this made with AI?"
  always gets an honest answer.
- Test before claiming it works. Done = deployed and the live version verified, not "code done".
```

## Make this better

These are ours, and they will keep changing. If you have working agreements with your coding agent that held up, or one of ours failed for you, we'd like to hear it: [github.com/RichardTheuws/ai-toolkit/discussions](https://github.com/RichardTheuws/ai-toolkit/discussions).

---

*Written with Claude, checked by Richard.*
