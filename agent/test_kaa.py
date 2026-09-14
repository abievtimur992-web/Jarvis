"""
test_kaa.py — kaa.py ushın stdlib unittest testleri.

Iske túsiriw: python test_kaa.py  (yamasa: python -m unittest test_kaa)
"""

import unittest

import kaa


class TestCasefold(unittest.TestCase):
    def test_ascii_i_becomes_dotless(self):
        self.assertEqual(kaa.casefold("I"), "ı")

    def test_dotted_i_becomes_plain_i(self):
        self.assertEqual(kaa.casefold("İ"), "i")

    def test_accented_letters(self):
        self.assertEqual(kaa.casefold("Á"), "á")
        self.assertEqual(kaa.casefold("Ǵ"), "ǵ")
        self.assertEqual(kaa.casefold("Ń"), "ń")

    def test_digraph(self):
        self.assertEqual(kaa.casefold("Sh"), "sh")
        self.assertEqual(kaa.casefold("Ch"), "ch")

    def test_whole_word(self):
        self.assertEqual(kaa.casefold("ARKAN"), "arkan")
        self.assertEqual(kaa.casefold("TIMUR"), "tımur")

    def test_none_passthrough(self):
        self.assertIsNone(kaa.casefold(None))


class TestCyrToLat(unittest.TestCase):
    def test_basic_word(self):
        self.assertEqual(kaa.cyr_to_lat("аркан"), "arkan")

    def test_special_letters(self):
        self.assertEqual(kaa.cyr_to_lat("ғарезсиз"), "ǵarezsiz")
        self.assertEqual(kaa.cyr_to_lat("өнер"), "óner")

    def test_sh_ch(self):
        self.assertEqual(kaa.cyr_to_lat("шаңарақ"), "shańaraq")
        self.assertEqual(kaa.cyr_to_lat("час"), "chas")

    def test_soft_hard_sign_dropped(self):
        self.assertEqual(kaa.cyr_to_lat("объект"), "obekt")


class TestMatchKey(unittest.TestCase):
    def test_latin_and_cyrillic_match(self):
        self.assertEqual(kaa.match_key("ARKAN"), kaa.match_key("АРКАН"))

    def test_lookalike_letters_fold(self):
        self.assertEqual(kaa.match_key("qapı"), kaa.match_key("qapi"))
        self.assertEqual(kaa.match_key("bahası"), kaa.match_key("bahasi"))

    def test_apostrophe_stripped(self):
        self.assertEqual(kaa.match_key("qo'ng'iroq"), kaa.match_key("qongiroq"))

    def test_empty(self):
        self.assertEqual(kaa.match_key(""), "")
        self.assertEqual(kaa.match_key(None), "")


class TestStem(unittest.TestCase):
    def test_agglutination_example(self):
        self.assertEqual(kaa.stem("klientlerimizge"), "klient")

    def test_plural_only(self):
        self.assertEqual(kaa.stem("qapılar"), "qapı")

    def test_dative(self):
        # dative suffix -ke/-ge qıyıladı
        self.assertTrue(kaa.stem("úyge").startswith("úy"))

    def test_never_below_three_letters(self):
        # "atı" (onıń atı) — qıysa "at" qaladı (3 áripten kem emes bolıwı msh)
        result = kaa.stem("at")
        self.assertEqual(result, "at")  # bul sózdiń o'zi 3 áripten kishi, qıyılmaydı

    def test_short_word_untouched(self):
        self.assertEqual(kaa.stem("úy"), "úy")


class TestNumToWords(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(kaa.num_to_words(0), "nol")

    def test_single_digits(self):
        self.assertEqual(kaa.num_to_words(1), "bir")
        self.assertEqual(kaa.num_to_words(9), "toǵız")

    def test_ten(self):
        self.assertEqual(kaa.num_to_words(10), "on")

    def test_compound_tens(self):
        self.assertEqual(kaa.num_to_words(25), "jigirma bes")

    def test_hundred(self):
        self.assertEqual(kaa.num_to_words(100), "júz")
        self.assertEqual(kaa.num_to_words(125), "júz jigirma bes")
        self.assertEqual(kaa.num_to_words(250), "eki júz eliw")

    def test_thousand(self):
        self.assertEqual(kaa.num_to_words(1000), "bir mıń")

    def test_money_example_from_spec(self):
        self.assertEqual(
            kaa.num_to_words(1250000),
            "bir million eki júz eliw mıń",
        )

    def test_negative(self):
        self.assertEqual(kaa.num_to_words(-5), "minus bes")


class TestToSpeakable(unittest.TestCase):
    def test_money(self):
        result = kaa.to_speakable("Bahası 1 250 000 som boladı.")
        self.assertIn("bir million eki júz eliw mıń som", result)

    def test_date(self):
        result = kaa.to_speakable("Kelisim 11-sentyabr kúni tayar boladı.")
        self.assertIn("on bir sentyabr", result)

    def test_percent(self):
        result = kaa.to_speakable("Ósim 25% boldı.")
        self.assertIn("jigirma bes procent", result)

    def test_plain_number(self):
        result = kaa.to_speakable("Bizde 3 xızmetker bar.")
        self.assertIn("úsh xızmetker", result)

    def test_empty(self):
        self.assertEqual(kaa.to_speakable(""), "")
        self.assertEqual(kaa.to_speakable(None), "")


class TestToKazakhCyrillic(unittest.TestCase):
    def test_basic_mapping(self):
        self.assertEqual(kaa.to_kazakh_cyrillic("arkan"), "аркан")

    def test_special_letters(self):
        self.assertEqual(kaa.to_kazakh_cyrillic("ǵa"), "ға")
        self.assertEqual(kaa.to_kazakh_cyrillic("ómir"), "өмір")

    def test_sh_ch(self):
        self.assertEqual(kaa.to_kazakh_cyrillic("shańaraq"), "шаңарақ")
        self.assertEqual(kaa.to_kazakh_cyrillic("chas"), "час")

    def test_case_insensitive(self):
        self.assertEqual(
            kaa.to_kazakh_cyrillic("ARKAN"),
            kaa.to_kazakh_cyrillic("arkan"),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
