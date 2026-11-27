"""Shared helpers for clean.py, check.py and voice.py: load the lexicon and detect the language."""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
LEX = os.path.join(HERE, "lexicon.json")

WORD_RE = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?")

NL_MARKERS = {"de", "het", "een", "en", "van", "ik", "je", "jij", "niet", "dat", "is",
              "op", "voor", "met", "wij", "we", "ook", "maar", "naar", "bij", "zijn",
              "wat", "geen", "nog", "dan", "om", "die", "deze", "jullie", "u", "uw"}
EN_MARKERS = {"the", "a", "an", "and", "of", "i", "you", "not", "that", "is", "on",
              "for", "with", "we", "also", "but", "to", "at", "are", "what", "no",
              "this", "it", "your", "my", "they", "was"}
LANGS = ("en", "nl")


def default_lang():
    """The tie-break language: LI_DEFAULT_LANG if it is 'en' or 'nl', otherwise 'en'."""
    lang = os.environ.get("LI_DEFAULT_LANG", "en").strip().lower()
    return lang if lang in LANGS else "en"


def load_lexicon(path=LEX):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def words(text):
    return WORD_RE.findall(text)


def detect_lang(text):
    """'nl' or 'en' based on function words. On a tie: default_lang() ('en' unless LI_DEFAULT_LANG says otherwise)."""
    w = [x.lower() for x in words(text)]
    nl = sum(1 for x in w if x in NL_MARKERS)
    en = sum(1 for x in w if x in EN_MARKERS)
    if en > nl:
        return "en"
    if nl > en:
        return "nl"
    return default_lang()


def for_lang(entries, lang):
    """Entries that apply to this language ('any' always applies)."""
    return [e for e in entries if e.get("lang", "en") in (lang, "any")]


def term_pattern(find):
    return re.compile(r"\b" + re.escape(find).replace(r"\ ", r"\s+") + r"\b", re.IGNORECASE)
