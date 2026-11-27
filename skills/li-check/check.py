#!/usr/bin/env python3
"""
check.py - quality and transparency check for a draft, before it goes out.

Based on detect.py from Jake Schincariol's linkedin-agent-skill (MIT).
The original scored how "human" text looks to AI detectors. That goal is
dropped here: we never hide AI use. What remains are the signals about
writing quality, plus a transparency gate.

Four checks, each 0-100, higher is better:

  VARIATION  variation in sentence length. Monotone reads badly.
  CONCRETE   numbers, names, amounts per 100 words. Abstract says nothing.
  HOLLOW     hits from lexicon.json per 100 words.
  VOICE      personal form (I/we/you) and no template structures.
             English contractions only count for English text.

Two more checks for a post (from 80 words), see voice.py:

  COHERENCE  sentence length, long sentences and connectives against the author's own
             writing baseline (LI_VOICE, default ~/.config/li-check/voice.json).
             No baseline, or a baseline in another language: n/a.
  TEMPLATE   the shape against the last five posts (LI_HISTORY). Same length, paragraphs,
             punchy opener and closing question: the same template. No history: n/a.

These two are signals: they show in the output but do not count towards the total and the
verdict. A series may deliberately keep one shape, and short sentences can be well written.

Transparency gate: if the text denies AI use, contains an open {{placeholder}},
or references private internal data, the verdict is always REWRITE, whatever
the score.

Verdict: OK (total 70+ and no check below 55, gate clean) or REWRITE.
Exit code 0 for OK, 1 for REWRITE.

Usage
  python3 check.py draft.txt
  python3 check.py before.txt after.txt
  pbpaste | python3 check.py - --json
  python3 check.py draft.txt --voice voice.json --history ~/folder/with/posts
"""

import argparse
import json
import os
import re
import statistics
import sys

import voice
from clean import scan
from common import LEX, detect_lang, for_lang, load_lexicon, term_pattern, words

SENT_RE = re.compile(r"[^.!?\n]+[.!?]*")
CONTRACTIONS = re.compile(r"\b\w+'(?:s|t|re|ve|ll|d|m)\b", re.IGNORECASE)
PRONOUNS = {
    "en": re.compile(r"\b(i|me|my|mine|we|us|our|you|your)\b", re.IGNORECASE),
    "nl": re.compile(r"\b(ik|mij|me|mijn|we|wij|ons|onze|je|jij|jou|jouw|u|uw|jullie)\b", re.IGNORECASE),
}
NUMBERS = re.compile(r"\b\d[\d,.]*%?|[€$]\s?\d")
NUMBER_WORDS = re.compile(
    r"\b(?:twee|drie|vier|vijf|zes|zeven|acht|negen|tien|elf|twaalf|twintig|dertig|veertig|"
    r"vijftig|honderd|duizend|miljoen|two|three|four|five|six|seven|eight|nine|ten|twelve|"
    r"twenty|thirty|fifty|hundred|thousand|million)\b", re.IGNORECASE)
PROPER = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-zà-ÿ]{2,}\b", re.MULTILINE)

CHECKS = ["VARIATION", "CONCRETE", "HOLLOW", "VOICE", "COHERENCE", "TEMPLATE"]
# Signals do not count towards the total and the verdict. A different shape is the writer's
# choice, not a requirement; these checks only show how far a draft is from the author's own
# baseline and from the most recent posts. A well-written series can score low on both.
SIGNALS = ("COHERENCE", "TEMPLATE")
# Sentence-length variation only means something in a longer text; a DM of four sentences
# would otherwise be rejected on it unfairly. Checks that are n/a do not count.
MIN_SENTENCES = 6


def clamp(n):
    return max(0.0, min(100.0, n))


def scale(value, good, bad):
    if good == bad:
        return 50.0
    return clamp((value - bad) / (good - bad) * 100)


def sentences(text):
    return [s.strip() for s in SENT_RE.findall(text) if len(s.split()) > 2]


def check_variation(text):
    lens = [len(s.split()) for s in sentences(text)]
    if len(lens) < MIN_SENTENCES:
        return None, f"n/a below {MIN_SENTENCES} sentences"
    mean = statistics.mean(lens)
    cv = statistics.pstdev(lens) / mean if mean else 0
    return scale(cv, good=0.70, bad=0.22), f"variation {cv:.2f} over {len(lens)} sentences (aim for 0.55+)"


def check_concrete(text):
    w = words(text)
    if len(w) < 25:
        return None, "n/a below 25 words"
    hits = (len(NUMBERS.findall(text)) + len(NUMBER_WORDS.findall(text))
            + len(set(PROPER.findall(text))))
    density = hits * 100 / len(w)
    return scale(density, good=6.0, bad=0.5), f"{hits} concrete markers, {density:.1f} per 100 words (aim for 4+)"


def check_hollow(text, lex):
    w = words(text)
    if not w:
        return 50.0, "empty"
    hits, found = 0, []
    for entry in lex["words"] + lex["phrases"]:
        n = len(term_pattern(entry["find"]).findall(text))
        if n:
            hits += n
            found.append(entry["find"])
    density = hits * 100 / len(w)
    detail = f"{hits} hollow terms, {density:.1f} per 100 words"
    if found:
        detail += " (" + ", ".join(sorted(found)[:4]) + (", ..." if len(found) > 4 else "") + ")"
    return scale(density, good=0.0, bad=4.0), detail


def check_voice(text, lex, lang):
    w = words(text)
    if len(w) < 25:
        return None, "n/a below 25 words"
    per100 = 100 / len(w)
    person = len(PRONOUNS[lang].findall(text)) * per100
    tells = scan(text, for_lang(lex["structures"], lang))
    n_tells = sum(t["count"] for t in tells)
    bullets = [len(b.split()) for b in re.findall(r"(?m)^\s*[-*•]\s+(.+)$", text)]
    uniform = len(bullets) >= 3 and statistics.pstdev(bullets) < 1.6
    structure = clamp(100 - n_tells * 22)
    if lang == "en":
        contractions = len(CONTRACTIONS.findall(text)) * per100
        score = (scale(contractions, good=3.0, bad=0.0) * 0.35
                 + scale(person, good=8.0, bad=1.0) * 0.35 + structure * 0.30)
        detail = f"{contractions:.1f} contractions, {person:.1f} personal pronouns per 100 words"
    else:
        score = scale(person, good=8.0, bad=1.0) * 0.55 + structure * 0.45
        detail = f"{person:.1f} personal pronouns per 100 words"
    names = [t["id"] for t in tells]
    if uniform:
        score -= 12
        names.append("uniform-bullets")
    detail += f", {n_tells} template structure(s)"
    if names:
        detail += " [" + ", ".join(names[:4]) + "]"
    return clamp(score), detail


def coherence(text, baseline, lang):
    """COHERENCE only compares like with like: the draft and the baseline must be in the same language."""
    if baseline and voice.baseline_lang(baseline) != lang:
        return None, f"n/a: baseline is '{voice.baseline_lang(baseline)}', draft is '{lang}'"
    return voice.check_coherence(text, baseline, lang)


def run(text, lex, baseline=None, history=None):
    """baseline = the author's writing baseline (voice.json), history = features of past posts. Without: n/a."""
    lang = detect_lang(text)
    results = {
        "VARIATION": check_variation(text),
        "CONCRETE": check_concrete(text),
        "HOLLOW": check_hollow(text, lex),
        "VOICE": check_voice(text, lex, lang),
        "COHERENCE": coherence(text, baseline, lang),
        "TEMPLATE": voice.check_template(text, history),
    }
    scores = [results[c][0] for c in CHECKS if results[c][0] is not None and c not in SIGNALS]
    overall = statistics.mean(scores) * 0.6 + min(scores) * 0.4
    gate = scan(text, lex.get("transparency", []))
    verdict = "OK" if (overall >= 70 and min(scores) >= 55 and not gate) else "REWRITE"
    return results, overall, verdict, gate, lang


def bar(score, width=24):
    filled = round(score / 100 * width)
    return "#" * filled + "." * (width - filled)


def render(results, overall, verdict, gate, lang, label=None, out=sys.stdout):
    title = f"QUALITY CHECK  (language: {lang})" + (f"  -  {label}" if label else "")
    print("\n" + title, file=out)
    print("=" * max(len(title), 62), file=out)
    for name in CHECKS:
        score, detail = results[name]
        if score is None:
            print(f"  {name:<12} {'n/a':>30}", file=out)
        else:
            print(f"  {name:<12} {bar(score)} {score:5.1f}" + ("   (signal, does not count)" if name in SIGNALS else ""), file=out)
        print(f"  {'':<12} {detail}", file=out)
    print("-" * 62, file=out)
    print(f"  {'TOTAL':<12} {bar(overall)} {overall:5.1f}   {verdict}", file=out)
    if gate:
        print("\n  TRANSPARENCY GATE CLOSED:", file=out)
        for g in gate:
            print(f"    - {g['name']}: {g['fix']}", file=out)
    elif verdict != "OK":
        weakest = min((c for c in CHECKS if results[c][0] is not None and c not in SIGNALS), key=lambda c: results[c][0])
        print(f"\n  Weakest point: {weakest}. Start there.", file=out)
    print("", file=out)


def main():
    ap = argparse.ArgumentParser(description="Quality and transparency check for a draft.")
    ap.add_argument("input", nargs="?", default="-", help="file, or - for stdin")
    ap.add_argument("compare", nargs="?", help="second file, for before/after")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    ap.add_argument("--lexicon", default=LEX, help="path to lexicon.json")
    ap.add_argument("--voice", default=voice.VOICE, help="the author's writing baseline (voice.py build); env LI_VOICE")
    ap.add_argument("--history", default=voice.HISTORY,
                    help="folder with past posts (*/post.md, or *.md/*.txt); env LI_HISTORY")
    args = ap.parse_args()

    lex = load_lexicon(args.lexicon)
    read = lambda p: sys.stdin.read() if p == "-" else open(p, encoding="utf-8").read()
    targets = [(args.input, read(args.input))]
    if args.compare:
        targets.append((args.compare, read(args.compare)))

    payload = []
    for name, text in targets:
        results, overall, verdict, gate, lang = run(text, lex, voice.load_baseline(args.voice),
                                                    voice.load_history(args.history, exclude=text))
        payload.append({
            "source": name, "lang": lang,
            "checks": {k: {"score": None if v[0] is None else round(v[0], 1), "detail": v[1]} for k, v in results.items()},
            "score": round(overall, 1), "verdict": verdict,
            "transparency": gate,
        })
        if not args.json:
            render(results, overall, verdict, gate, lang,
                   label=os.path.basename(name) if args.compare else None)

    if args.json:
        print(json.dumps(payload if args.compare else payload[0], indent=2, ensure_ascii=False))
    elif args.compare:
        a, b = payload
        print(f"  {a['score']:.1f} {a['verdict']}  ->  {b['score']:.1f} {b['verdict']}"
              f"   ({b['score'] - a['score']:+.1f})\n")
    sys.exit(0 if payload[-1]["verdict"] == "OK" else 1)


if __name__ == "__main__":
    main()
