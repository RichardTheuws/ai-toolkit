#!/usr/bin/env python3
"""
clean.py - clean up a draft for readability. Not to hide AI use.

Based on humanize.py from Jake Schincariol's linkedin-agent-skill (MIT).
Deliberately left out: the typography pass (dashes, curly quotes). It only
changed text to look less "machine-made", and that is camouflage, not quality.

Two passes, in this order:

  1. INVISIBLE  remove zero-width characters, soft hyphens, BOMs and Unicode
                tags. They break search, hashtags and copy-paste. Non-breaking
                spaces become normal spaces.
  2. HOLLOW     replace hollow words from lexicon.json with plain words, only
                in the language of the text. Capitalisation and URLs stay
                intact. Hollow language from the other language (for example
                "leverage" in a Dutch post) is reported, not translated.

Reported, never rewritten automatically: sentence structures (triads, "not only
X but also Y", reflex questions) and transparency violations (denying that AI
helped write it, open {{placeholders}}, references to private internal data).

Usage
  python3 clean.py draft.txt
  python3 clean.py draft.txt --report
  python3 clean.py draft.txt -o clean.txt
  pbpaste | python3 clean.py - --json
"""

import argparse
import json
import re
import sys

from common import LEX, detect_lang, for_lang, load_lexicon, term_pattern

URL_RE = re.compile(r"https?://\S+|www\.\S+|\S+@\S+\.\S+")
SENT_RE = re.compile(r"[^.!?\n]+[.!?]*")


def _cp(spec):
    if "-" in spec:
        a, b = spec.split("-")
        return (int(a[2:], 16), int(b[2:], 16))
    return int(spec[2:], 16)


def protect_urls(text):
    found = []

    def stash(m):
        found.append(m.group(0))
        return f"\x00URL{len(found) - 1}\x00"

    return URL_RE.sub(stash, text), found


def restore_urls(text, found):
    for i, url in enumerate(found):
        text = text.replace(f"\x00URL{i}\x00", url)
    return text


def pass_invisible(text, lex):
    hits = []
    for entry in lex["invisible"]:
        cp = _cp(entry["cp"])
        if isinstance(cp, tuple):
            pattern = "[" + re.escape(chr(cp[0])) + "-" + re.escape(chr(cp[1])) + "]"
        elif cp == 0x200D:
            # A ZWJ between emoji (👨‍💻) is part of the emoji: leave it.
            pattern = r"(?<![\U0001F000-\U0001FAFF☀-➿️])‍"
        else:
            pattern = re.escape(chr(cp))
        n = len(re.findall(pattern, text))
        if n:
            repl = " " if entry.get("action") == "space" else ""
            text = re.sub(pattern, repl, text)
            hits.append({"name": entry["name"], "count": n, "action": entry.get("action", "delete")})
    return text, hits


def _match_case(src, repl):
    if not repl:
        return repl
    if src.isupper() and len(src) > 1:
        return repl.upper()
    if src[0].isupper():
        return repl[0].upper() + repl[1:]
    return repl


def pass_lexical(text, lex, lang):
    """Replace hollow language in the text's own language; report the other language's."""
    hits, foreign = [], []
    entries = sorted(lex["phrases"] + lex["words"], key=lambda e: len(e["find"]), reverse=True)
    for entry in entries:
        pattern = term_pattern(entry["find"])
        found = pattern.findall(text)
        if not found:
            continue
        if entry.get("lang", "en") not in (lang, "any"):
            foreign.append({"find": entry["find"], "count": len(found)})
            continue
        hits.append({"find": entry["find"], "replace": entry["replace"] or "(removed)",
                     "count": len(found), "family": entry["family"]})
        text = pattern.sub(lambda m: _match_case(m.group(0), entry["replace"]), text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"(?m)^[ \t]*([,.;:])\s*", "", text)
    text = re.sub(r"[ \t]+([,.;:!?])", r"\1", text)
    text = re.sub(r"(?m)^[ \t]+$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text, hits, foreign


def scan(text, rules):
    flags = []
    for s in rules:
        try:
            pattern = re.compile(s["regex"], re.MULTILINE)
        except re.error:
            continue
        n = len(pattern.findall(text))
        if n:
            flags.append({"id": s["id"], "name": s["name"], "count": n, "fix": s["fix"]})
    return flags


def scan_structures(text, lex, lang):
    flags = scan(text, for_lang(lex["structures"], lang))
    lens = [len(s.split()) for s in SENT_RE.findall(text) if len(s.split()) > 2]
    if len(lens) >= 4:
        mean = sum(lens) / len(lens)
        var = sum((n - mean) ** 2 for n in lens) / len(lens)
        cv = (var ** 0.5) / mean if mean else 0
        if cv < 0.35:
            flags.append({"id": "monotone", "name": f"Monotone sentence length (variation {cv:.2f})",
                          "count": len(lens),
                          "fix": "Split one sentence in two, let another run on. Monotone reads badly."})
    return flags


def clean(text, lex):
    lang = detect_lang(text)
    text, urls = protect_urls(text)
    text, inv = pass_invisible(text, lex)
    text, lexi, foreign = pass_lexical(text, lex, lang)
    text = restore_urls(text, urls)
    return text.strip() + "\n", {
        "lang": lang,
        "invisible": inv,
        "lexical": lexi,
        "foreign": foreign,
        "structures": scan_structures(text, lex, lang),
        "transparency": scan(text, lex.get("transparency", [])),
    }


def render_report(report, out=sys.stderr):
    def head(title):
        print(f"\n{title}\n" + "-" * len(title), file=out)

    head(f"CLEANUP REPORT  (language: {report['lang']})")
    if report["transparency"]:
        head("STOP - TRANSPARENCY  (this does not go out)")
        for h in report["transparency"]:
            print(f"  {h['count']:>3}x  {h['name']}\n        {h['fix']}", file=out)
    if report["invisible"]:
        head("1. INVISIBLE CHARACTERS")
        for h in report["invisible"]:
            print(f"  {h['count']:>3}x  {h['name']}  -> {h['action']}", file=out)
    if report["lexical"]:
        head("2. HOLLOW LANGUAGE REPLACED")
        for h in report["lexical"]:
            print(f"  {h['count']:>3}x  {h['find']}  -> {h['replace']}   [{h['family']}]", file=out)
    if report["foreign"]:
        head("3. HOLLOW LANGUAGE FROM THE OTHER LANGUAGE  (rewrite yourself)")
        for h in report["foreign"]:
            print(f"  {h['count']:>3}x  {h['find']}", file=out)
    if report["structures"]:
        head("4. SENTENCE STRUCTURES  (not automatic - rewrite yourself)")
        for h in report["structures"]:
            print(f"  {h['count']:>3}x  {h['name']}\n        {h['fix']}", file=out)
    if not any(report[k] for k in ("invisible", "lexical", "foreign", "structures", "transparency")):
        print("  Nothing to clean up.", file=out)
    print("", file=out)


def main():
    ap = argparse.ArgumentParser(description="Clean up a draft for readability (not to hide AI use).")
    ap.add_argument("input", nargs="?", default="-", help="file, or - for stdin")
    ap.add_argument("-o", "--out", help="write the cleaned text here")
    ap.add_argument("--report", action="store_true", help="show what changed (stderr)")
    ap.add_argument("--json", action="store_true", help="print {text, report} as JSON")
    ap.add_argument("--lexicon", default=LEX, help="path to lexicon.json")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
    text, report = clean(raw, load_lexicon(args.lexicon))

    if args.json:
        print(json.dumps({"text": text, "report": report}, indent=2, ensure_ascii=False))
        return
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"written: {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    if args.report:
        render_report(report)


if __name__ == "__main__":
    main()
