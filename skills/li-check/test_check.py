"""Tests for clean.py and check.py.  Run: python3 -m unittest -v (in this folder)."""

import os
import unittest
from unittest import mock

from check import run
from clean import clean
from common import detect_lang, load_lexicon

LEX = load_lexicon()

# Dutch drafts: the tool works on Dutch and English text.
NL_BAD = """In het huidige digitale tijdperk is een naadloze en robuuste oplossing cruciaal.
Wij optimaliseren processen en tillen uw bedrijf naar een hoger niveau.
Het is niet alleen software, het is een partnerschap.
Het resultaat?
Herkenbaar?"""

NL_GOOD = """Vorige week belde Sanne van Brouwer Metaal (fictief voorbeeld).
Hun planning zat verspreid over drie Excel-bestanden, en elke maandagochtend ging op aan het gelijktrekken ervan, terwijl de werkvloer al stond te wachten.
Een hele ochtend. Elke week.
We bouwden in vier weken één planbord dat alles bij elkaar zet. Nu kost het tien minuten.
Ik schrijf dit met hulp van AI, de cijfers en het verhaal zijn van mij.
Waar zit bij jou de maandagochtend die je kwijt bent aan overtikken?"""

EN_BAD = """In today's fast-paced world, a seamless and robust solution is crucial.
We leverage cutting-edge synergy to unlock your potential.
It's not just software, it's a partnership.
The result?
Thoughts?"""

EN_GOOD = """Last week Sanne from Brouwer Metal called me (a made-up example).
Their planning was spread over three Excel files, and every Monday morning went into lining them up while the shop floor stood waiting.
A whole morning. Every week.
We built one planning board in four weeks that puts it all in one place. Now it takes ten minutes.
I write this with help from AI; the numbers and the story are mine.
Where's the Monday morning you lose to retyping?"""


class TestLanguage(unittest.TestCase):
    def test_dutch(self):
        self.assertEqual(detect_lang(NL_GOOD), "nl")

    def test_english(self):
        self.assertEqual(detect_lang("We shipped it and you can use it today, it is not hard."), "en")

    def test_tie_defaults_to_english(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LI_DEFAULT_LANG", None)
            self.assertEqual(detect_lang("Excel Bladwijzer 2026"), "en")

    def test_tie_break_is_configurable(self):
        with mock.patch.dict(os.environ, {"LI_DEFAULT_LANG": "nl"}):
            self.assertEqual(detect_lang("Excel Bladwijzer 2026"), "nl")
        with mock.patch.dict(os.environ, {"LI_DEFAULT_LANG": "xx"}):
            self.assertEqual(detect_lang("Excel Bladwijzer 2026"), "en")


class TestClean(unittest.TestCase):
    def test_replaces_dutch_hollow_language(self):
        text, rep = clean(NL_BAD, LEX)
        self.assertIn("soepele", text)
        self.assertNotIn("cruciaal", text.lower())
        self.assertTrue(text.startswith("Nu is een"))

    def test_replaces_english_hollow_language(self):
        text, rep = clean(EN_BAD, LEX)
        self.assertEqual(rep["lang"], "en")
        self.assertNotIn("seamless", text.lower())
        self.assertNotIn("crucial", text.lower())
        self.assertTrue(rep["lexical"])

    def test_leaves_dashes_alone(self):
        text, _ = clean("Dit werkt — en dat blijft zo.", LEX)
        self.assertIn("—", text)

    def test_leaves_curly_quotes_alone(self):
        text, _ = clean("She said “it works” and that’s it.", LEX)
        self.assertIn("“it works”", text)
        self.assertIn("that’s", text)

    def test_does_not_translate_english_in_dutch_text(self):
        text, rep = clean("We gaan dit leverage voor de klant, dat is de bedoeling van het plan.", LEX)
        self.assertIn("leverage", text)
        self.assertEqual([f["find"] for f in rep["foreign"]], ["leverage"])

    def test_removes_zero_width_but_not_emoji_zwj(self):
        text, _ = clean("Hallo​wereld 👨‍💻 klaar", LEX)
        self.assertIn("Hallowereld", text)
        self.assertIn("👨‍💻", text)

    def test_url_stays_intact(self):
        text, _ = clean("Lees https://example.com/cruciaal-naadloos voor de details.", LEX)
        self.assertIn("https://example.com/cruciaal-naadloos", text)

    def test_dutch_structures_reported(self):
        _, rep = clean(NL_BAD, LEX)
        ids = {s["id"] for s in rep["structures"]}
        self.assertTrue({"nl-not-just-it-is", "nl-the-reveal", "nl-reflex-question"} <= ids)

    def test_english_structures_reported(self):
        _, rep = clean(EN_BAD, LEX)
        ids = {s["id"] for s in rep["structures"]}
        self.assertTrue({"not-just", "the-result", "engagement-bait"} <= ids)


class TestCheck(unittest.TestCase):
    def test_good_dutch_draft_ok(self):
        _, score, verdict, gate, lang = run(NL_GOOD, LEX)
        self.assertEqual((verdict, gate, lang), ("OK", [], "nl"), score)

    def test_good_english_draft_ok(self):
        _, score, verdict, gate, lang = run(EN_GOOD, LEX)
        self.assertEqual((verdict, gate, lang), ("OK", [], "en"), score)

    def test_bad_drafts_rewrite(self):
        self.assertEqual(run(NL_BAD, LEX)[2], "REWRITE")
        self.assertEqual(run(EN_BAD, LEX)[2], "REWRITE")

    def test_gate_denies_ai(self):
        _, _, verdict, gate, _ = run(NL_GOOD + "\nDeze post is 100% zelf geschreven, geen AI gebruikt.", LEX)
        self.assertEqual(verdict, "REWRITE")
        self.assertIn("denies-ai", {g["id"] for g in gate})
        _, _, verdict, gate, _ = run(EN_GOOD + "\nThis post was written without AI.", LEX)
        self.assertEqual(verdict, "REWRITE")
        self.assertIn("denies-ai", {g["id"] for g in gate})

    def test_gate_placeholder(self):
        _, _, verdict, gate, _ = run(NL_GOOD + "\nWe bespaarden {{jouw getal}} uur.", LEX)
        self.assertEqual(verdict, "REWRITE")
        self.assertIn("placeholder", {g["id"] for g in gate})

    def test_gate_private_data(self):
        _, _, verdict, gate, _ = run(NL_GOOD + "\nIn mijn notities zag ik dat je CFO bent.", LEX)
        self.assertEqual(verdict, "REWRITE")
        self.assertIn("private-data", {g["id"] for g in gate})
        _, _, verdict, gate, _ = run(EN_GOOD + "\nAccording to my CRM you're the CFO.", LEX)
        self.assertEqual(verdict, "REWRITE")
        self.assertIn("private-data", {g["id"] for g in gate})

    def test_short_dm_not_rejected_on_sentence_length(self):
        dm = ("Hoi Bas, mooi om te zien dat je sinds eind 2022 Brouwer Metaal runt, met barbecues voor de horeca uit een familiebedrijf van 1974.\n"
              "Bij maatwerk uit de werkplaats lopen offerte en planning vaak net niet gelijk.\n"
              "Daar bouw ik met AI kleine systemen voor, gewoon bij jou in de regio Eindhoven.\n"
              "Zin in een bak koffie in Veldhoven?")
        results, _, verdict, _, _ = run(dm, LEX)
        self.assertIsNone(results["VARIATION"][0])
        self.assertEqual(verdict, "OK")

    def test_short_hollow_dm_stays_rewrite(self):
        _, _, verdict, _, _ = run("Hoi! Wij bieden naadloze, robuuste en baanbrekende oplossingen. Interesse?", LEX)
        self.assertEqual(verdict, "REWRITE")

    def test_mentioning_ai_is_fine(self):
        _, _, _, gate, _ = run("Ik maak deze berichten met hulp van AI en lees alles zelf na.", LEX)
        self.assertEqual(gate, [])
        _, _, _, gate, _ = run("I write these posts with help from AI and read every word myself.", LEX)
        self.assertEqual(gate, [])


if __name__ == "__main__":
    unittest.main()
