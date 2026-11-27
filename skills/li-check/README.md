# li-check

A quality and transparency check for LinkedIn drafts (posts, comments, replies,
DMs, profile text), packaged as a Claude Code skill. It works on English and
Dutch text, runs on the Python standard library, and never touches the network.

It does three things:

1. **Cleans** a draft: removes invisible characters (zero-width spaces, soft
   hyphens, BOMs, Unicode tag smuggling) and replaces hollow phrases
   ("seamless", "in today's fast-paced world", "naadloos") with plain words from
   a bilingual lexicon.
2. **Reports** what only a person should rewrite: template sentences ("It's not
   just X, it's Y"), staged reveals ("The result?"), reflex questions
   ("Thoughts?"), monotone sentence length.
3. **Scores** the draft on variation, concreteness, hollow language and voice,
   plus two signals against the author's own writing (coherence with their
   baseline, and whether it repeats the shape of their recent posts). Then it
   gives a verdict: **OK** or **REWRITE**.

## Why there is a transparency gate

We never hide AI use. This tool makes text better, not invisible.

The project it is forked from scored how "human" a text looks to AI detectors.
That goal is gone. Instead there is a hard gate: if a draft denies or hides AI
use ("100% human-written", "no AI used"), still contains an open
`{{placeholder}}`, or references private internal data ("according to my CRM",
"in my notes"), the verdict is REWRITE no matter how well it scores. Mentioning
that you used AI is always fine.

For the same reason it deliberately does **not** change dashes, curly quotes or
other typography. Doing that only serves to look less machine-made. That is
camouflage, not quality. And the skill refuses requests to "make this
undetectable".

## Install

```bash
cp -r li-check ~/.claude/skills/
```

Claude Code picks it up as the `li-check` skill. You can also run the scripts
directly; they need Python 3.8+ and nothing else.

## Usage

```bash
cd ~/.claude/skills/li-check
python3 clean.py draft.txt -o clean.txt --report   # clean up, show what changed (report on stderr)
python3 check.py clean.txt                         # scores + verdict, exit code 0 = OK, 1 = REWRITE
python3 check.py draft.txt clean.txt               # before/after comparison
pbpaste | python3 check.py - --json                # from the clipboard, machine-readable
python3 voice.py show draft.txt                    # the raw features of one text
python3 -m unittest                                # run the tests
```

Example output (an English test draft from `test_check.py`):

```
QUALITY CHECK  (language: en)
==============================================================
  VARIATION    #################.......  70.4
               variation 0.56 over 7 sentences (aim for 0.55+)
  CONCRETE     ######################## 100.0
               8 concrete markers, 9.8 per 100 words (aim for 4+)
  HOLLOW       ######################## 100.0
               0 hollow terms, 0.0 per 100 words
  VOICE        #################.......  69.7
               1.2 contractions, 6.1 personal pronouns per 100 words, 0 template structure(s)
  COHERENCE                               n/a
               n/a: no baseline (python3 voice.py build <your own texts>)
  TEMPLATE                                n/a
               n/a: fewer than 3 previous posts to compare with (set LI_HISTORY)
--------------------------------------------------------------
  TOTAL        ###################.....  78.9   OK
```

### Scoring

The total is 60% the mean of the counted checks plus 40% the weakest one,
because one hollow sentence takes a whole message down. **OK** needs a total of
70 or more, no check below 55, and a clean transparency gate. Checks that do not
apply to a short text (a four-line DM has no meaningful sentence variation) are
n/a and do not count. COHERENCE and TEMPLATE are signals: they show in the
output but never change the total or the verdict.

### Configuration

| variable | default | what |
| --- | --- | --- |
| `LI_VOICE` | `~/.config/li-check/voice.json` | the author's writing baseline |
| `LI_HISTORY` | unset (TEMPLATE is n/a) | folder with past posts: `*/post.md`, or `*.md` / `*.txt`, sorted by name, newest last |
| `LI_DEFAULT_LANG` | `en` | language to use when detection is a tie (`en` or `nl`) |

`check.py --voice` and `--history` override the environment, and `--lexicon`
points at another lexicon file.

## Build your voice baseline

COHERENCE compares a draft with how *you* write when nobody is scoring: sentence
length, share of long sentences, and how often a sentence connects to the
previous one ("but", "because", "then", "maar", "omdat", ...). Build it once from
at least five texts you wrote yourself, of 150+ words each: old blog posts,
long emails, essays. Markdown with frontmatter is fine.

```bash
python3 voice.py build ~/writing/*.md                 # -> ~/.config/li-check/voice.json
python3 voice.py build --out voice.json --min-words 200 a.md b.md c.md d.md e.md
```

The baseline records its language (the majority language of the texts) and only
uses texts in that language. A draft in another language gets COHERENCE n/a.
Keep the file out of any repo; it describes your writing.

For TEMPLATE, point `LI_HISTORY` at a folder with your published posts. With at
least three past posts it compares the draft's shape with the last five.

## Known limits

- Language detection counts function words. It knows English and Dutch only;
  other languages fall back to the tie-break language.
- The lexicon is a list, not understanding. A listed word can be the right word;
  if you use one on purpose, remove it from `lexicon.json`.
- CONCRETE counts capitalised words as names. German nouns, sentence-initial
  words after line breaks and acronyms can push it up or down.
- The transparency gate is pattern-based. It catches the common phrasings of
  denying AI use or leaking private data, not every possible one. It is a
  backstop, not a substitute for reading your own text.
- Scores are a check afterwards, never the goal. A text that scores well and does
  not read well is not good.

## Make this better

Found a hollow phrase that should be in the lexicon, a false positive, or a
language you want supported? Open a thread in
[Discussions](https://github.com/RichardTheuws/ai-toolkit/discussions).

## License and notice

MIT, see [LICENSE](LICENSE).

NOTICE: li-check is a fork of `/li-human` from Jake Schincariol's
[linkedin-agent-skill](https://github.com/Jakeschincariol/linkedin-agent-skill)
(MIT). The detector-evasion parts were removed and a transparency gate, Dutch
support and the voice checks were added.
