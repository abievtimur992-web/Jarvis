"""
kaa.py — Qaraqalpaq tili ushın bir orın.

Bul faylda Jarvis-tiń qaraqalpaqsha tekstpen islesetuǵın barlıq function-ları
jıynalǵan: durıs kishi árip qılıw, izlew ushın kilt jasaw, jalǵawlardı
qıyıw (stemming), kirill-latın transliteraciya, sanlardı sózge aylandırıw
hám qazaqsha dawıs ushın harip almastırıw.

Bul fayl basqa hesh nárseni bilmeydi — tek tekst penen isleydi. Sonıń ushın
onı test_kaa.py penen bólek tekseriwge boladı.
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# 1) casefold — Qaraqalpaqsha durıs kishi árip qılıw
# ---------------------------------------------------------------------------
#
# Mashqala: Python-dıń qábıl str.lower() function-ı "İ" (noqatlı úlken I) ni
# "i" + jasırın noqat belgisine (eki simvolǵa) aylandıradı, al bizge tek "i"
# kerek. Sonday-aq "I" (noqatsız úlken I) qaraqalpaqshada "ı" ǵa aylanıwı
# kerek, al Python onı "i" ge aylandıradı. Sonlıqtan hár bir háripti özimiz
# qolmen islewimiz kerek.

def casefold(s: str | None) -> str | None:
    """Qaraqalpaqsha durıs kishi árip qılıw. 'I' -> 'ı', 'İ' -> 'i'."""
    if s is None:
        return s
    out = []
    for ch in s:
        if ch == "İ":
            out.append("i")
        elif ch == "I":
            out.append("ı")
        else:
            out.append(ch.lower())
    return "".join(out)


# ---------------------------------------------------------------------------
# 2) cyr_to_lat — Qaraqalpaq kirillinen latınǵa
# ---------------------------------------------------------------------------
#
# Dıqqat: bul Qaraqalpaq kirilli ushın, orıs tili ushın EMES. Orıs tekstin
# osı arqalı ótkerse nadurıs shıǵadı (mısalı orısshada Y hámishe "ı" emes).

_CYR_TO_LAT_MAP: dict[str, str] = {
    "А": "A", "а": "a",
    "Ә": "Á", "ә": "á",
    "Б": "B", "б": "b",
    "В": "V", "в": "v",
    "Г": "G", "г": "g",
    "Ғ": "Ǵ", "ғ": "ǵ",
    "Д": "D", "д": "d",
    "Е": "E", "е": "e",
    "Ж": "J", "ж": "j",
    "З": "Z", "з": "z",
    "И": "I", "и": "i",
    "Й": "Y", "й": "y",
    "К": "K", "к": "k",
    "Қ": "Q", "қ": "q",
    "Л": "L", "л": "l",
    "М": "M", "м": "m",
    "Н": "N", "н": "n",
    "Ң": "Ń", "ң": "ń",
    "О": "O", "о": "o",
    "Ө": "Ó", "ө": "ó",
    "П": "P", "п": "p",
    "Р": "R", "р": "r",
    "С": "S", "с": "s",
    "Т": "T", "т": "t",
    "У": "U", "у": "u",
    "Ү": "Ú", "ү": "ú",
    "Ў": "W", "ў": "w",
    "Ф": "F", "ф": "f",
    "Х": "X", "х": "x",
    "Ҳ": "H", "ҳ": "h",
    "Ц": "C", "ц": "c",
    "Ч": "Ch", "ч": "ch",
    "Ш": "Sh", "ш": "sh",
    # Ы-nıń latın sáykesi anıq emes ("Í/ı"), biz "ı" nı kóbirek qollanamız
    "Ы": "I", "ы": "ı",
    "Э": "E", "э": "e",
    "Ю": "Yu", "ю": "yu",
    "Я": "Ya", "я": "ya",
    "Ъ": "", "ъ": "",
    "Ь": "", "ь": "",
}


def cyr_to_lat(s: str | None) -> str | None:
    """Qaraqalpaq kirill tekstin latınǵa audaradı. Basqa háripler ózgermeydi."""
    if not s:
        return s
    return "".join(_CYR_TO_LAT_MAP.get(ch, ch) for ch in s)


def _has_cyrillic(s: str) -> bool:
    return any("Ѐ" <= ch <= "ӿ" for ch in s)


# ---------------------------------------------------------------------------
# 3) match_key — izlew ushın kılt (tek izlew ushın, ekranǵa shıǵarılmaydı)
# ---------------------------------------------------------------------------

_APOSTROPHE_CHARS = "'ʻʼ`´‘’"

# Izlewde uqsas háripler bir-birine aylanadı (klaviaturada belgi joq bolsa da
# tabılsın dep): á/a, í/ı/i, ó/o, ú/u, ń/n, ǵ/g
_LOOKALIKE_FOLD = {
    "á": "a",
    "í": "i",
    "ı": "i",
    "ó": "o",
    "ú": "u",
    "ń": "n",
    "ǵ": "g",
}


def match_key(s: str | None) -> str:
    """
    Eki tekstiñ "bir söz" ekenin biliw ushın kılt jasaydı: NFC-normalizaciya,
    kirillden latınǵa audarıw, durıs kishi árip qılıw, uqsas háriplerdi
    birlestiriw hám apostrof variantların alıp taslaw.

    Bul TEK izlew ushın — ekranǵa shıǵarılatuǵın tekst hámishe originaldıń
    özi bolıwı kerek.
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    if _has_cyrillic(s):
        s = cyr_to_lat(s)
    s = casefold(s) or ""
    out = []
    for ch in s:
        if ch in _APOSTROPHE_CHARS:
            continue
        out.append(_LOOKALIKE_FOLD.get(ch, ch))
    return "".join(out)


# ---------------------------------------------------------------------------
# 4) stem — jalǵawlardı qıyıw (agglyutinaciyanı izlew ushın buzıw)
# ---------------------------------------------------------------------------
#
# Tártip: qaraqalpaqshada söz dúzilisi TUBIR + kóplik + tiyislilik + kelis
# bolǵanı ushın, qıyıwdı sońınan (kelisten) baslaymız.

_CASE_SUFFIXES = sorted(
    [
        "dıń", "diń", "nıń", "niń", "tıń", "tiń",
        "ǵa", "ge", "qa", "ke", "na", "ne",
        "dı", "di", "nı", "ni", "tı", "ti",
        "da", "de", "ta", "te",
        "dan", "den", "tan", "ten", "nan", "nen",
        "menen", "benen", "penen",
    ],
    key=len,
    reverse=True,
)

_POSSESSIVE_SUFFIXES = sorted(
    [
        "ımız", "imiz",
        "ıń", "iń", "sı", "si", "ım", "im",
        "ı", "i",
    ],
    key=len,
    reverse=True,
)

_PLURAL_SUFFIXES = sorted(
    ["lar", "ler", "dar", "der", "tar", "ter"],
    key=len,
    reverse=True,
)

_MIN_STEM_LEN = 3


def _strip_one(word: str, suffixes: list[str]) -> str:
    for suf in suffixes:
        if word.endswith(suf) and len(word) - len(suf) >= _MIN_STEM_LEN:
            return word[: -len(suf)]
    return word


def stem(word: str | None) -> str:
    """
    Sózdiń tùbirin tabıwǵa háreket etedi: kelis -> tiyislilik -> kóplik
    jalǵawların qıyadı. 3 áripten kishi tùbirge sheken qıymaydı.

    Mısalı: "klientlerimizge" -> "klient"
    """
    if not word:
        return ""
    if len(word) <= _MIN_STEM_LEN:
        return word
    w = word
    w = _strip_one(w, _CASE_SUFFIXES)
    w = _strip_one(w, _POSSESSIVE_SUFFIXES)
    w = _strip_one(w, _PLURAL_SUFFIXES)
    return w


# ---------------------------------------------------------------------------
# 5) num_to_words — sandı sózge aylandırıw
# ---------------------------------------------------------------------------

_ONES = {
    1: "bir", 2: "eki", 3: "úsh", 4: "tórt", 5: "bes",
    6: "altı", 7: "jeti", 8: "segiz", 9: "toǵız",
}
_TENS = {
    1: "on", 2: "jigirma", 3: "otız", 4: "qırıq", 5: "eliw",
    6: "alpıs", 7: "jetpis", 8: "seksen", 9: "toqsan",
}
_SCALES = [(10 ** 9, "milliard"), (10 ** 6, "million"), (10 ** 3, "mıń")]


def _three_digit_words(n: int) -> list[str]:
    """0..999 aralıǵındaǵı sandı sóz dizimine aylandıradı."""
    parts: list[str] = []
    hundreds, rem = divmod(n, 100)
    if hundreds:
        if hundreds > 1:
            parts.append(_ONES[hundreds])
        parts.append("júz")
    tens, ones = divmod(rem, 10)
    if tens:
        parts.append(_TENS[tens])
    if ones:
        parts.append(_ONES[ones])
    return parts


def num_to_words(n: int) -> str:
    """Pútin sandı qaraqalpaqsha sózge aylandıradı. Mısalı: 25 -> 'jigirma bes'."""
    if n == 0:
        return "nol"
    negative = n < 0
    n = abs(int(n))

    words: list[str] = []
    remaining = n
    for value, name in _SCALES:
        if remaining >= value:
            count = remaining // value
            remaining %= value
            words.extend(_three_digit_words(count))
            words.append(name)
    words.extend(_three_digit_words(remaining))

    if not words:
        words = ["nol"]
    result = " ".join(words)
    if negative:
        result = "minus " + result
    return result


# ---------------------------------------------------------------------------
# 6) to_speakable — sanlardı, aqshanı, sánelerdi sóz penen jazıw
# ---------------------------------------------------------------------------
#
# Bul function tekstti dawısqa jiberer aldında qollanıladı. Ekranǵa hesh
# qashan shıǵarılmaydı hám saqlanbaydı — tek dawıs ushın.

_DATE_RE = re.compile(r"\b(\d{1,2})-([A-Za-zÁÓÚŃǴáóúńǵ]+)\b")
_PERCENT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
_MONEY_RE = re.compile(r"(\d{1,3}(?:[  ]\d{3})+|\d+)\s*som\b", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\d{1,3}(?:[  ]\d{3})+|\d+")


def to_speakable(s: str | None) -> str:
    """Sandı, aqshanı, sáne hám procentti sózge aylandırıp, dawıs ushın tayarlaydı."""
    if not s:
        return s or ""
    result = s

    def _date_repl(m: re.Match) -> str:
        day = int(m.group(1))
        month = m.group(2)
        return f"{num_to_words(day)} {month}"

    result = _DATE_RE.sub(_date_repl, result)

    def _percent_repl(m: re.Match) -> str:
        raw = m.group(1).replace(",", ".")
        if "." in raw:
            whole, frac = raw.split(".", 1)
            words = f"{num_to_words(int(whole))} pútin {num_to_words(int(frac))}"
        else:
            words = num_to_words(int(raw))
        return f"{words} procent"

    result = _PERCENT_RE.sub(_percent_repl, result)

    def _money_repl(m: re.Match) -> str:
        digits = m.group(1).replace(" ", "").replace(" ", "")
        return f"{num_to_words(int(digits))} som"

    result = _MONEY_RE.sub(_money_repl, result)

    def _number_repl(m: re.Match) -> str:
        digits = m.group(0).replace(" ", "").replace(" ", "")
        if not digits.isdigit():
            return m.group(0)
        return num_to_words(int(digits))

    result = _NUMBER_RE.sub(_number_repl, result)

    return result


# ---------------------------------------------------------------------------
# 7) to_kazakh_cyrillic — dawıs kópiri (Qazaq dawısı ushın harip almastırıw)
# ---------------------------------------------------------------------------
#
# Qaraqalpaq tili ushın tayar dawıs xızmeti joq. Sonlıqtan Qazaq dawısı
# arqalı sóylew ushın, Qaraqalpaqsha háriplerdi Qazaqsha kirillge
# "audaramız" — bul durıs audarma emes, tek dıbıstı jaqınlastırıw. Bul
# keste — bir GIPOTEZA, qulaq penen tekserip ózgertiw kerek boladı.

_KAA_TO_KAZ_SINGLE = {
    "a": "а", "á": "ә", "b": "б", "d": "д", "e": "е", "f": "ф",
    "g": "г", "ǵ": "ғ", "h": "һ", "x": "х", "ı": "ы", "i": "і",
    "j": "ж", "k": "к", "q": "қ", "l": "л", "m": "м", "n": "н",
    "ń": "ң", "o": "о", "ó": "ө", "p": "п", "r": "р", "s": "с",
    "t": "т", "u": "ұ", "ú": "ү", "v": "в", "w": "у", "y": "й",
    "z": "з", "c": "ц",
}


def to_kazakh_cyrillic(s: str | None) -> str:
    """
    Qaraqalpaqsha latın tekstti Qazaq dawısı ushın kirillge aylandıradı.
    Bul faqat dawıs (TTS) ushın qollanıladı — ekranǵa shıǵarılmaydı.
    """
    if not s:
        return s or ""
    text = casefold(s) or ""
    text = text.replace("sh", "ш").replace("ch", "ч")
    return "".join(_KAA_TO_KAZ_SINGLE.get(ch, ch) for ch in text)
