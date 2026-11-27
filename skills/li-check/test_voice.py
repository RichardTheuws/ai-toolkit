"""Tests for voice.py and how check.py uses it.  Run: python3 -m unittest -v (in this folder)."""

import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

import voice
from check import run
from common import load_lexicon

LEX = load_lexicon()

# Dutch sample posts: one in short staccato sentences, one in long connected sentences.
STACCATO = """47.862 formules. Zoveel staan er in mijn sjablonen.

Een goede sheet rekent snel. Mijn sjablonen werkten. Een sheet knelt pas later.

Drie versies van dezelfde lijst. Niemand weet welke klopt.

Eén collega die weet hoe het zit. Is die er niet, dan staat het werk stil.

Gegevens die je overtypt. Van lijst naar offerte. Van offerte naar factuur.

Herken jij er twee? Dan is het tijd. Tijd om te kijken wat een eigen systeem oplevert.

Je sheet is het begin. Niet het probleem. De gegevens gaan mee. Je formules ook.

Begin met één sheet. Welke kost jou de meeste tijd?

Geschreven met AI-hulp, gelezen en verstuurd door mij."""

LOPEND = """Ik ben groot geworden met Excel, en toch help ik bedrijven tegenwoordig om het te vervangen, omdat een sheet die jarenlang goed werkte vanzelf gaat knellen zodra meer mensen ermee moeten werken.

Dat komt niet doordat Excel slecht rekent, want mijn offertesjablonen telden bijna vijftigduizend formules en ze deden precies wat ze moesten doen, maar een sheet is gemaakt voor één persoon die weet hoe hij in elkaar zit.

Toen wij met meer mensen offertes gingen maken, ontstonden er drie versies van dezelfde lijst, en daarna wist niemand meer welke versie de juiste was, zodat we elke week tijd kwijt waren aan het vergelijken van bestanden die eigenlijk hetzelfde hadden moeten zijn.

Daarom begin ik bij een klant nooit met het weggooien van zijn sheet, maar met de vraag welke berekening erin zit die hij zelf heeft bedacht, want daar zit zijn ervaring in en die moet mee naar het nieuwe systeem.

Geschreven met AI-hulp, gelezen en verstuurd door mij."""

FLOWING_EN = """I grew up with spreadsheets, and yet these days I help companies replace them, because a sheet that worked well for years starts to pinch as soon as more people have to work in it at the same time.

That is not because the spreadsheet calculates badly, since my quote templates held almost fifty thousand formulas and they did exactly what they had to do, but a sheet is made for one person who knows how it fits together.

When more of us started making quotes, three versions of the same list appeared, and after that nobody knew which version was the right one, so we lost time every week comparing files that should have been identical.

That is why I never start by throwing away a client's sheet, but with the question which calculation in it they came up with themselves, because that is where their experience lives and it has to come along to the new system.

Written with help from AI, read and sent by me."""

BASELINE = {"texts": 40, "sentence_length": {"median": 17.1, "lower": 15.4}, "long": {"median": 35.3, "lower": 27.6},
            "connected": {"median": 33.3, "lower": 19.3}}  # no "lang": treated as Dutch


class TestFeatures(unittest.TestCase):
    def test_ai_line_does_not_count_and_frontmatter_is_dropped(self):
        k = voice.features("---\nstatus: done\n---\n" + STACCATO)
        self.assertEqual(k["paragraphs"], 8)
        self.assertTrue(k["question_close"])
        self.assertEqual(k["first_sentence"], 2)
        self.assertLess(k["sentence_length"], 8)

    def test_flowing_text_has_long_connected_sentences(self):
        k = voice.features(LOPEND)
        self.assertGreater(k["sentence_length"], 25)
        self.assertEqual(k["connected"], 100.0)
        self.assertFalse(k["question_close"])

    def test_english_connectives_and_ai_line(self):
        k = voice.features(FLOWING_EN)
        self.assertEqual(k["paragraphs"], 4)
        self.assertEqual(k["connected"], 100.0)

    def test_too_short_gives_no_features(self):
        self.assertIsNone(voice.features("Hoi Piet. Dank voor je bericht. Ik bel je morgen."))

    def test_markup_and_links_do_not_count_as_words(self):
        self.assertEqual(voice.bare("# Kop\n\nZie [de **uitleg**](https://x.nl/a-b) en <b>meer</b>."), "Zie de uitleg en  meer .")


class TestCoherence(unittest.TestCase):
    def test_staccato_drops_and_flowing_passes(self):
        low, detail = voice.check_coherence(STACCATO, BASELINE)
        high, _ = voice.check_coherence(LOPEND, BASELINE)
        self.assertLess(low, 30)
        self.assertEqual(high, 100.0)
        self.assertIn("baseline 17.1", detail)

    def test_no_baseline_or_short_text_is_na(self):
        self.assertIsNone(voice.check_coherence(LOPEND, None)[0])
        short = "Dank voor je reactie. Ik zie het ook zo. Maar het hangt af van de klant. Wat denk jij? Ik hoor het graag. Tot snel."
        self.assertIsNone(voice.check_coherence(short, BASELINE)[0])

    def test_building_a_baseline_needs_enough_texts(self):
        baseline = voice.build_baseline([LOPEND * 2] * 6)
        self.assertEqual(baseline["texts"], 6)
        self.assertEqual(baseline["lang"], "nl")
        self.assertGreater(baseline["sentence_length"]["lower"], 25)
        with self.assertRaises(ValueError):
            voice.build_baseline([LOPEND * 2] * 3)

    def test_english_baseline(self):
        baseline = voice.build_baseline([FLOWING_EN * 2] * 5)
        self.assertEqual(baseline["lang"], "en")
        self.assertEqual(voice.check_coherence(FLOWING_EN, baseline)[0], 100.0)

    def test_build_command_writes_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for i in range(5):
                p = os.path.join(tmp, "t%d.md" % i)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(LOPEND * 2)
                paths.append(p)
            out = os.path.join(tmp, "sub", "voice.json")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(voice.main(["build", "--out", out] + paths), 0)
            self.assertEqual(voice.load_baseline(out)["texts"], 5)
        self.assertIsNone(voice.load_baseline("/does/not/exist.json"))


class TestTemplate(unittest.TestCase):
    def test_same_shape_as_previous_posts_drops(self):
        history = [voice.features(STACCATO)] * 5
        score, detail = voice.check_template(STACCATO, history)
        self.assertEqual(score, 0.0)
        self.assertIn("6 of 6", detail)

    def test_different_shape_passes(self):
        history = [voice.features(STACCATO)] * 5
        score, _ = voice.check_template(LOPEND, history)
        self.assertGreaterEqual(score, 90)

    def test_too_little_history_is_na(self):
        self.assertIsNone(voice.check_template(STACCATO, [voice.features(STACCATO)] * 2)[0])
        self.assertIsNone(voice.check_template(STACCATO, None)[0])

    def test_loading_history_without_the_text_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i, text in enumerate([STACCATO, LOPEND, STACCATO.replace("47.862", "12")]):
                os.makedirs(os.path.join(tmp, "2026-11-0%d-x" % (i + 1)))
                with open(os.path.join(tmp, "2026-11-0%d-x" % (i + 1), "post.md"), "w", encoding="utf-8") as f:
                    f.write("---\nstatus: done\n---\n" + text)
            self.assertEqual(len(voice.load_history(tmp)), 3)
            self.assertEqual(len(voice.load_history(tmp, exclude=LOPEND)), 2)
        self.assertEqual(voice.load_history("/does/not/exist"), [])

    def test_history_as_flat_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in (("01.md", STACCATO), ("02.txt", LOPEND), ("03.md", FLOWING_EN)):
                with open(os.path.join(tmp, name), "w", encoding="utf-8") as f:
                    f.write(text)
            loaded = voice.load_history(tmp)
            self.assertEqual(len(loaded), 3)
            self.assertEqual(loaded[1]["connected"], 100.0)  # sorted by name: 02.txt is LOPEND

    def test_no_history_folder_means_na(self):
        with mock.patch.object(voice, "HISTORY", None):
            self.assertEqual(voice.load_history(None), [])
            self.assertIsNone(run(STACCATO, LEX, None, voice.load_history())[0]["TEMPLATE"][0])


class TestInCheck(unittest.TestCase):
    def test_without_baseline_and_history_both_are_na(self):
        results, _, _, _, _ = run(STACCATO, LEX)
        self.assertIsNone(results["COHERENCE"][0])
        self.assertIsNone(results["TEMPLATE"][0])

    def test_coherence_and_template_are_signals_and_do_not_change_the_verdict(self):
        history = [voice.features(STACCATO)] * 5
        without = run(STACCATO, LEX)
        with_ = run(STACCATO, LEX, BASELINE, history)
        self.assertLess(with_[0]["COHERENCE"][0], 55)
        self.assertLess(with_[0]["TEMPLATE"][0], 55)
        self.assertEqual((with_[1], with_[2]), (without[1], without[2]))  # same total, same verdict

    def test_english_text_gets_no_dutch_baseline(self):
        en = ("We shipped the new planning board last week and it already saves the team an hour a day. " * 6)
        results, _, _, _, _ = run(en, LEX, BASELINE, None)
        self.assertIsNone(results["COHERENCE"][0])
        self.assertIn("baseline is 'nl'", results["COHERENCE"][1])


if __name__ == "__main__":
    unittest.main()
