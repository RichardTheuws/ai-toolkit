#!/usr/bin/env python3
"""
voice.py - two checks that measure whether a post flows, and whether it is the same template again.

COHERENCE  compares a draft with the author's own writing baseline (voice.json): how long the
           sentences are, how many long sentences there are, and how many sentences connect to
           the previous one with a connective (but, because, so, then, after that ...).
           The baseline comes from texts the author wrote, not from a general norm.
TEMPLATE   compares the shape of a draft with the most recent posts: length, number of
           paragraphs, paragraph length, a short punchy opener, a question as the close, the
           share of short sentences. If the draft matches what just went out on nearly every
           point, it is the same template.

Why: a run of posts can each score 95+ on the other checks and still read as the same post,
in short staccato sentences that are far from how the author writes when nobody is scoring.
These two checks make that visible.

Build the baseline from your own texts (Markdown with or without frontmatter, or plain text):
  python3 voice.py build ~/path/to/own-texts/*.md              # -> ~/.config/li-check/voice.json
  python3 voice.py build --out voice.json --min-words 150 a.md b.md
Show the features of one text:
  python3 voice.py show draft.txt

Paths (environment):
  LI_VOICE    the baseline file (default ~/.config/li-check/voice.json)
  LI_HISTORY  a folder with past posts: one subfolder per post containing post.md, or one
              .md/.txt file per post, sorted by name (oldest first). Unset: TEMPLATE is n/a.

A score is a check afterwards, never the goal: a text that scores well and does not read well
is not good.
"""

import argparse
import glob
import json
import os
import re
import statistics
import sys

from common import detect_lang

VOICE = os.path.expanduser(os.environ.get("LI_VOICE", "~/.config/li-check/voice.json"))
HISTORY = os.path.expanduser(os.environ["LI_HISTORY"]) if os.environ.get("LI_HISTORY") else None

SENTENCE = re.compile(r"[^.!?\n]+[.!?]*")
WORD = re.compile(r"[a-zà-ÿ]+")
CONNECTIVES = {
    "nl": frozenset(
        "maar want dus omdat toen daarna daarom terwijl hoewel doordat zodat daardoor bovendien "
        "echter toch namelijk immers vervolgens eerst later uiteindelijk inmiddels intussen "
        "tenslotte kortom althans trouwens overigens sindsdien waardoor waarna zodra voordat nadat "
        "totdat tenzij mits ofwel oftewel daarmee daarvoor daarbij hierdoor desondanks".split()),
    "en": frozenset(
        "but because so since when then therefore while although though whereas thus however "
        "yet still meanwhile moreover besides instead otherwise afterwards later finally eventually "
        "first until unless before after once whereby hence nevertheless nonetheless anyway "
        "meantime consequently".split()),
}
LONG = 20          # a long sentence: from this many words
SHORT = 5          # a short sentence: up to and including this many words
MIN_SENTENCES = 4  # a post in long sentences has few of them; exactly those must count
MIN_WORDS = 80     # below this length it is not a post but a comment or message
PREVIOUS = 5       # the shape is compared with this many previous posts
AI_LINE = re.compile(
    r"\bAI\b.*\b(geschreven|gelezen|nagekeken|gemaakt|hulp|written|read|checked|edited|made|help|assist\w*)\b"
    r"|\b(geschreven|gemaakt|written|made)\b.*\bAI\b",
    re.IGNORECASE)


def bare(text):
    """Strip frontmatter, markup, headings, links and HTML; the paragraph layout stays."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2]
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(?m)^#+ .*$", "", text)
    return re.sub(r"[*_`>|]", "", text).strip()


def sentences(text):
    return [s.strip() for s in SENTENCE.findall(text) if WORD.search(s.lower())]


def paragraphs(text):
    """Paragraphs without the AI line at the end: it belongs to every post and says nothing about the shape."""
    ps = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    while ps and len(ps[-1].split()) <= 16 and AI_LINE.search(ps[-1]):
        ps.pop()
    return ps


def features(text, lang=None):
    """The writing measures and the shape of one text, or None if there is too little to say anything."""
    text = bare(text)
    ps = paragraphs(text)
    body = "\n\n".join(ps)
    s = sentences(body)
    if len(s) < MIN_SENTENCES:
        return None
    connectives = CONNECTIVES[lang or detect_lang(body)]
    lengths = [len(x.split()) for x in s]
    connected = sum(1 for x in s if connectives & set(WORD.findall(x.lower())))
    close = ps[-1] if ps else ""
    return {
        "words": len(body.split()),
        "sentence_length": round(statistics.mean(lengths), 1),
        "long": round(100 * sum(1 for n in lengths if n >= LONG) / len(s), 1),
        "short": round(100 * sum(1 for n in lengths if n <= SHORT) / len(s), 1),
        "connected": round(100 * connected / len(s), 1),
        "paragraphs": len(ps),
        "paragraph_length": statistics.median(len(p.split()) for p in ps),
        "first_sentence": lengths[0],
        "question_close": "?" in close,
    }


# ── the author's own baseline ───────────────────────────────────────────────────────────────
def quartile(values, q):
    s = sorted(values)
    i = (len(s) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def build_baseline(texts, min_words=150):
    """Median and lower quartile of sentence length, long sentences and connected sentences over own texts."""
    langs = [detect_lang(bare(t)) for t in texts]
    lang = max(("en", "nl"), key=langs.count) if langs else "en"
    k = [x for x in (features(t, lang) for t, tl in zip(texts, langs) if tl == lang) if x and x["words"] >= min_words]
    if len(k) < 5:
        raise ValueError("too few usable texts for a baseline (%d, at least 5 needed)" % len(k))
    baseline = {"texts": len(k), "lang": lang}
    for field in ("sentence_length", "long", "connected"):
        w = [x[field] for x in k]
        baseline[field] = {"median": round(statistics.median(w), 1), "lower": round(quartile(w, 0.25), 1)}
    return baseline


def load_baseline(path=None):
    path = path or VOICE
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def baseline_lang(baseline):
    return (baseline or {}).get("lang", "nl")


def scale(value, good, bad):
    if good == bad:
        return 50.0
    return max(0.0, min(100.0, (value - bad) / (good - bad) * 100))


def check_coherence(text, baseline, lang=None):
    """(score, detail). 100 = at or above the lower quartile of the baseline; 0 = at a third of it."""
    if not baseline:
        return None, "n/a: no baseline (python3 voice.py build <your own texts>)"
    k = features(text, lang or baseline_lang(baseline))
    if not k or k["words"] < MIN_WORDS:
        return None, "n/a below %d words or %d sentences" % (MIN_WORDS, MIN_SENTENCES)
    parts = []
    for field in ("sentence_length", "long", "connected"):
        good = baseline[field]["lower"]
        parts.append(scale(k[field], good, good / 3))
    score = statistics.mean(parts)
    detail = ("%.1f words per sentence (baseline %.1f), %.0f%% long sentences (%.0f%%), %.0f%% sentences with a "
              "connective (%.0f%%)" % (k["sentence_length"], baseline["sentence_length"]["median"], k["long"],
                                       baseline["long"]["median"], k["connected"], baseline["connected"]["median"]))
    return score, detail


# ── the same template ───────────────────────────────────────────────────────────────────────
def history_files(folder):
    """One entry per past post: <folder>/*/post.md, or <folder>/*.md and *.txt. Sorted by name, newest last."""
    found = glob.glob(os.path.join(folder, "*", "post.md"))
    found += glob.glob(os.path.join(folder, "*.md")) + glob.glob(os.path.join(folder, "*.txt"))
    return sorted(found, key=lambda p: os.path.relpath(p, folder))


def load_history(folder=None, exclude=""):
    """Features of the most recent posts, without the text being checked right now. No folder: []."""
    folder = folder or HISTORY
    if not folder:
        return []
    out = []
    exclude = bare(exclude).strip()
    for path in history_files(folder):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if exclude and bare(text).strip() == exclude:
            continue
        k = features(text)
        if k:
            out.append(k)
    return out


POINTS = (
    ("length", lambda k, h: abs(k["words"] - h["words"]) <= 0.35 * h["words"]),
    ("number of paragraphs", lambda k, h: abs(k["paragraphs"] - h["paragraphs"]) <= 3),
    ("paragraph length", lambda k, h: abs(k["paragraph_length"] - h["paragraph_length"]) <= 8),
    ("short punchy opener", lambda k, h: k["first_sentence"] <= 15 and h["first_sentence"] <= 15),
    ("question as close", lambda k, h: k["question_close"] and h["question_close"]),
    ("share of short sentences", lambda k, h: abs(k["short"] - h["short"]) <= 8),
)
TEMPLATE_SCORE = {0: 100.0, 1: 100.0, 2: 90.0, 3: 70.0, 4: 45.0, 5: 20.0, 6: 0.0}


def check_template(text, history):
    """(score, detail). The more shape points match the most recent posts, the lower."""
    k = features(text)
    if not k or k["words"] < MIN_WORDS:
        return None, "n/a below %d words or %d sentences" % (MIN_WORDS, MIN_SENTENCES)
    previous = (history or [])[-PREVIOUS:]
    if len(previous) < 3:
        return None, "n/a: fewer than 3 previous posts to compare with (set LI_HISTORY)"
    h = {field: statistics.median(v[field] for v in previous)
         for field in ("words", "paragraphs", "paragraph_length", "first_sentence", "short")}
    h["question_close"] = sum(1 for v in previous if v["question_close"]) * 2 > len(previous)
    same = [name for name, match in POINTS if match(k, h)]
    score = TEMPLATE_SCORE[len(same)]
    if not same:
        return score, "different shape from the last %d posts" % len(previous)
    return score, "%d of %d shape points match the last %d posts (%s)" % (
        len(same), len(POINTS), len(previous), ", ".join(same))


# ── command line ────────────────────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(description="Build your own writing baseline, or show the features of a text.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build the baseline from texts you wrote yourself (at least 5)")
    b.add_argument("files", nargs="+")
    b.add_argument("--out", default=VOICE, help="where to write it (default: LI_VOICE or ~/.config/li-check/voice.json)")
    b.add_argument("--min-words", type=int, default=150, help="ignore texts shorter than this")
    t = sub.add_parser("show", help="the features of one text")
    t.add_argument("file")
    a = ap.parse_args(argv)
    if a.cmd == "show":
        with open(a.file, encoding="utf-8") as fh:
            print(json.dumps(features(fh.read()), indent=2, ensure_ascii=False))
        return 0
    texts = []
    for p in a.files:
        with open(p, encoding="utf-8") as fh:
            texts.append(fh.read())
    baseline = build_baseline(texts, a.min_words)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(baseline, fh, indent=2, ensure_ascii=False)
    print("baseline from %d texts -> %s" % (baseline["texts"], a.out))
    print(json.dumps(baseline, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
