---
name: li-check
description: >-
  Quality and transparency check for a LinkedIn draft (post, comment, reply, DM,
  profile text) before the author sends it: hollow language out, more concrete,
  the author's own voice, and a hard transparency gate (never deny AI use, no open
  placeholders, no private internal data). Works on English and Dutch text. Use on
  every draft from the li-* skills, and when the author asks "check this", "is this
  hollow", "make this more concrete" or "can this go out like this".
---

# li-check

**What this is not for:** passing text off as not written with AI. The author is
always open about AI use. This skill makes text better, not invisible. If you get
a request like "make sure this isn't recognised as AI" or "make it undetectable",
don't do it: explain briefly why, and offer the quality check instead.

Three scripts in this folder, standard library only, nothing goes over the network:

```bash
python3 clean.py draft.txt -o clean.txt --report   # clean up, show what changed
python3 check.py clean.txt                         # four checks + two signals + transparency gate
python3 check.py draft.txt clean.txt               # before/after
python3 voice.py build ~/my-own-texts/*.md         # one-time: the author's writing baseline
python3 -m unittest                                # tests
```

`clean.py` and `check.py` read `lexicon.json`. Every entry has a `lang` (`en`,
`nl` or `any`). Replacements only happen in text of the same language. If the
author uses a listed word on purpose, remove it from the list.

Language is detected from function words. On a tie it falls back to English, or
to `LI_DEFAULT_LANG` (`en` or `nl`).

## What happens automatically

1. **Invisible characters removed.** Zero-width characters, soft hyphens, BOMs and
   Unicode tags break search, hashtags and copy-paste. Non-breaking spaces become
   normal spaces. A joiner inside an emoji stays.
2. **Hollow language replaced.** "Seamless", "crucial", "in today's digital age",
   "take it to the next level" and their Dutch counterparts become plain words.
   Hollow language from the other language (English buzzwords in a Dutch text) is
   reported, not translated, because that needs a rewrite.

**Deliberately not:** dashes, curly quotes and other typography stay as they are.
Changing them would only serve to make text look less machine-made. That is
camouflage, not quality.

## What gets reported (rewrite it yourself)

- Template sentences: "It's not just X, it's Y", "not only ... but also",
  "The result?" on its own line, the triad "X, Y, and Z." (and the Dutch versions).
- Reflex questions at the end: "Thoughts?", "Agree?", "Herkenbaar?", "Eens?".
- Cliches: "passionate about", "results-driven", "let that sink in".
- Monotone sentence length and bullets that are all the same length.

## The transparency gate

If any of these is in the text, the verdict is always **REWRITE**, whatever the score:

| rule | why |
| --- | --- |
| Denies or hides AI use ("100% human-written", "no AI used", "zelf geschreven, geen AI") | we never hide AI use |
| Open `{{placeholder}}` | a fact is missing, and making it up is not allowed |
| References private internal data ("in my notes", "according to my CRM", "in mijn notities") | only use what the person shared publicly or told the author directly |

Mentioning AI use is never a problem. "I write this with help from AI" keeps the
gate open.

## The checks

| check | measures | good is |
| --- | --- | --- |
| VARIATION | variation in sentence length (from 6 sentences) | short and long mixed |
| CONCRETE | numbers, number words, names, amounts per 100 words | 4+ |
| HOLLOW | lexicon hits per 100 words | 0 |
| VOICE | I/we/you form, no template sentences (contractions only for English) | personal and direct |
| COHERENCE | sentence length, long sentences and connectives against the author's own baseline; only for a post of 80+ words in the baseline's language | at or above the lower quartile of the author's own texts |
| TEMPLATE | the shape against the last five posts: length, paragraphs, punchy opener, closing question, short sentences | at most 3 of the 6 shape points the same |

**COHERENCE and TEMPLATE are signals.** They show in the output and do not count
towards the total or the verdict: a series of posts can deliberately keep one
shape and still be well written. Read them as: this is how far the draft is from
the author's own way of writing and from the latest posts. Whether that matters
is the writer's call.

The baseline is built once from texts the author wrote themselves (at least 5, of
150+ words): `python3 voice.py build <own texts>`. It is stored at `LI_VOICE`
(default `~/.config/li-check/voice.json`), never in the repo. Past posts for
TEMPLATE come from `LI_HISTORY`: a folder with one subfolder per post containing
`post.md`, or one `.md`/`.txt` file per post, sorted by name with the newest last.
Without a baseline or a history, COHERENCE and TEMPLATE are n/a and nothing
changes.

The total counts the mean of the checks for 60% and the **weakest check for 40%**,
because one hollow sentence takes a whole message down. **OK** needs a total of
70+, no check below 55 and a clean gate. Otherwise the verdict is **REWRITE**.
Checks that are n/a (too short a text) do not count. Exit code 0 for OK, 1 for
REWRITE.

## Order

1. `clean.py draft.txt -o clean.txt --report`
2. Is the gate closed? Fix that first. If a fact is missing, ask the author. Never
   make it up.
3. Rewrite the reported sentences yourself, keeping the meaning.
4. `check.py draft.txt clean.txt` for the before/after.
5. Show the author the text and the score, never only the score. Two rounds is
   normal. After five, the draft itself is the problem: write a new draft instead
   of another round.

Based on `/li-human` from Jake Schincariol's
[linkedin-agent-skill](https://github.com/Jakeschincariol/linkedin-agent-skill) (MIT).
