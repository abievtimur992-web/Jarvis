"""
business.py — struktura menen biznes maǵlıwmatı (BUSINESS DATA) hám erkin
biznes bilimi (BUSINESS KNOWLEDGE), iyeniń jeke jazbalarınan (PERSONAL
MEMORY, memory.py arqalı) bólek saqlanadı.

Úsh túrdiń parqı:
  PERSONAL MEMORY   — memory.py: "Men ... úyrenip atırman" sıyaqlı jeke
                       oylar, memory/*.md (dúz, hár qıylı sáne-fayllar).
  BUSINESS DATA     — usı fayl: struktura maydanlar (sales.monthly_sales
                       h.t.b.), memory/business_data/<biznes>.json.
  BUSINESS KNOWLEDGE — usı fayl: erkin tekst jazbalar (struktura maydanǵa
                       sıymaytuǵın faktlar), sol JSON-nıń "notes" bólimi.

Jazıw TEK usı modul arqalı boladı (memory.py-diń "jalǵız jazıwshı"
principi menen bir túrli) — hám TEK memory/ papkasına (iyeniń biznes/
papkasına Jarvis hesh qashan jazbaydı, bul qatań qaǵıyda).

Demo/real rejimnen ǵárezsiz: memory_dir() hámishe PROJECT_ROOT/memory
bolǵanı sıyaqlı, business_data da sol jerde — demo maǵlıwmatı menen
aralaspaydı.

SXEMA STANDARDIZATSIYASI (2-fazA): hár maydannıń endi úsh metadatası bar
— label (kórinetuǵın atı), type ("scalar" — bir qıymat, hámishe eń
soyǵısı jazıladı; "list" — tábiyiy túrde bir nesheden turıwı kerek,
biraq usı fazada háli tek scalar sıyaqlı bir "eń soyǵı jazba" saqlaydı,
append_to_list_field() KELESI fazada qosıladı — bul jerde tek BELGI),
description (bir gápte túsindirme). Eski (LEGACY) maydan atları
LEGACY_FIELD_ALIASES arqalı jańa atlarǵa avtomat kóshiriledi, derek
JOǴALMAYDI.

NUMERIC TÚRI (3-faza, BUSINESS DECISION ENGINE 1-basqıshı): finance/sales
bólimindegi bir qansha maydan (revenue, cost, gross_margin, fixed_costs,
cash_flow, monthly_sales, average_check, average_monthly_customers) endi
type="numeric". Bunday maydan ushın set_field() TOLIQ ÓZGERISSIZ qaladı
(eski, tekst jazba jolı — remember tool hám tools.py házirshe sonı
qollanadı, bul jumıs bузılmaydı). Struktура sandı jazıw ushın ARNAWLI,
qosımsha funktsiya bar — set_numeric_field(memory_dir, business_name,
field_key, value, unit) — {"value": <san>, "unit": <ólshem birligi>,
"updated_at": ...} formatında saqlaydı. Ólshem birligi NUMERIC_UNITS
dizimimen sheklengen (UZS, USD, KZT, percent, count) yamasa "unknown"
(belgisiz bolsa, ashıq usılay belgilenedi — hesh qashan ózinen oylap
tabılmaydı, "silently convert" islenbeydi). set_numeric_field ele
tools.py/remember-ge jalǵanbaǵan (bul — KELESI faza, Calculation Tool
menen birge).
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import os
import re
from pathlib import Path

import kaa

_SLUG_RE = re.compile(r"[^a-z0-9]+")

# ---------------------------------------------------------------------------
# Onboarding sxeması (Timur soraǵan A-H bólimleri, standartlastırılǵan)
# ---------------------------------------------------------------------------
#
# Hár maydan: {"label": ..., "type": "scalar"|"list", "description": ...}
#
# type="list" degeni — bul maydan tábiyiy túrde bir nesheden turadı
# (mısalı, bir biznesde bir nesha úskene boliwı múmkin). Házirshe (usı
# faza) LIST maydanlar da SCALAR sıyaqlı isleydi — set_field() hámishe
# tek "eń soyǵı jazba"nı saqlaydı, eskisi "previous"-ke ótedi. Kóp
# elementti dizim retinde QOSIP barıw (append_to_list_field) — KELESI
# faza, bul jerde ámelge asırılmaydı (Timur ózi ataylı sorap atır).

FIELD_SCHEMA = {
    "identity": {
        "label": "Biznes tuwralı",
        "fields": {
            "business_type": {"label": "Biznes túri", "type": "scalar", "description": "Biznes qaysı salada isleydi"},
            "location": {"label": "Jaylasqan jeri", "type": "scalar", "description": "Biznestiń jaylasqan jeri"},
            "years_operating": {"label": "Neshe jıldan beri isleydi", "type": "scalar", "description": "Biznestiń jası"},
            "owner": {"label": "Iyesi", "type": "scalar", "description": "Biznestiń iyesi"},
            "employees": {"label": "Xızmetkerler sanı", "type": "scalar", "description": "Komandadaǵı adam sanı"},
        },
    },
    "products": {
        "label": "Ónimler/xızmetler",
        "fields": {
            "categories": {"label": "Ónim kategoriyaları", "type": "scalar", "description": "Ónim túrleriniń ulıwma kategoriyaları"},
            "main_products": {"label": "Tiykarǵı ónimler", "type": "list", "description": "Biznestiń tiykarǵı ónimleri (birnesheden turıwı múmkin)"},
            "services": {"label": "Xızmetler", "type": "scalar", "description": "Kórsetiletuǵın xızmetler"},
            "production_capabilities": {"label": "Islep shıǵarıw múmkinshiligi", "type": "scalar", "description": "Islep shıǵarıw quwatı/múmkinshiligi"},
            "equipment": {"label": "Úskene", "type": "list", "description": "Biznestiń iyelik etetuǵın/qollanatuǵın úskeneleri (birnesheden turıwı múmkin)"},
        },
    },
    "customers": {
        "label": "Klientler",
        "fields": {
            "target_customers": {
                "label": "Maqsetli klientler",
                "type": "list",
                "description": "Biznes KIMGE satadı — tiykarǵı klient tipleri (mısalı: B2B firmalar, úy salıwshılar)",
            },
            "segments": {
                "label": "Klient segmentleri",
                "type": "list",
                "description": "Bar klientler QALAY bólinip qaraladı — segmentatsiya (mısalı: jańa/turaqlı, úlken/kishi buyırtpa)",
            },
            "average_monthly_customers": {"label": "Aylıq ortasha klient sanı", "type": "numeric", "description": "Bir ayda ortasha neshe klient"},
            "repeat_customers": {"label": "Qayta kelgen klientler", "type": "scalar", "description": "Qayta buyırtpa beretuǵın klientler dárejesi"},
        },
    },
    "sales": {
        "label": "Sawda",
        "fields": {
            "monthly_sales": {"label": "Aylıq sawda", "type": "numeric", "description": "Bir aydaǵı jalpı sawda summası"},
            "average_check": {"label": "Ortasha chek", "type": "numeric", "description": "Bir satıwdıń ortasha qunı"},
            "channels": {"label": "Sawda kanalları", "type": "scalar", "description": "Qalay satıladı (dúkan, online, tapsırıs h.t.b.)"},
            "seasonality": {"label": "Mawsımlıq", "type": "scalar", "description": "Jıl mawsımına baylanıslı ózgeris"},
            "conversion": {"label": "Konversiya", "type": "scalar", "description": "Qızıǵıwshılardıń qansha bólegi satıp aladı"},
            "leads": {"label": "Leadlar", "type": "scalar", "description": "Potensial klient aǵımı"},
        },
    },
    "finance": {
        "label": "Finans",
        "fields": {
            "revenue": {"label": "Kirim", "type": "numeric", "description": "Jalpı kirim"},
            "cost": {"label": "Shıǵın", "type": "numeric", "description": "Jalpı shıǵın"},
            "gross_margin": {"label": "Jalpı marja", "type": "numeric", "description": "Kirim menen tannarxı arasındaǵı parq, protsentte"},
            "fixed_costs": {"label": "Turaqlı shıǵınlar", "type": "numeric", "description": "Hár ay tákirarlanatuǵın shıǵınlar"},
            "debts": {"label": "Qarızlar", "type": "scalar", "description": "Bank krediti, tanıslardan qarız h.t.b."},
            "investments": {"label": "Investitsiyalar", "type": "scalar", "description": "Bizneske salınǵan qosımsha aqsha"},
            "cash_flow": {"label": "Aqsha aǵımı", "type": "numeric", "description": "Aqshanıń kiriw-shıǵıw teppesi"},
        },
    },
    "marketing": {
        "label": "Marketing",
        "fields": {
            "instagram": {"label": "Instagram", "type": "scalar", "description": "Instagram akkauntınıń jaǵdayı"},
            "telegram": {"label": "Telegram", "type": "scalar", "description": "Telegram kanalınıń jaǵdayı"},
            "advertising": {"label": "Reklama", "type": "scalar", "description": "Reklama/target jumısınıń jaǵdayı"},
            "acquisition_channels": {
                "label": "Klient tabıw kanalları",
                "type": "list",
                "description": "Klientler qaydan keledi — kanallar dizimi (mısalı: sarafan radio, Instagram, tanıslar)",
            },
            "competitors": {"label": "Baseketlesler", "type": "scalar", "description": "Nızıq baseketlesler haqqında maǵlıwmat"},
        },
    },
    "goals": {
        "label": "Maqsetler",
        "fields": {
            "current": {"label": "Házirgi/jaqın múddetli maqset", "type": "scalar", "description": "Házir hám jaqın arada (bir-eki ay) urınılatuǵın maqset"},
            "one_year": {"label": "1 jıllıq maqset", "type": "scalar", "description": "Kelesi 1 jıl ishinde jetiwi kerek maqset"},
            "strategic": {"label": "Strategiyalıq baǵdar", "type": "scalar", "description": "Uzaq múddetli, ulıwma strategiyalıq baǵdar"},
        },
    },
    "problems": {
        "label": "Mashqalalar",
        "fields": {
            "main": {"label": "Eń tiykarǵı mashqala", "type": "scalar", "description": "Házirgi waqıttaǵı eń úlken/tiykarǵı mashqala"},
            "bottlenecks": {"label": "Tarlawıq jerler", "type": "scalar", "description": "Jumıstı asıqtırıp turǵan tarlawıq jerler"},
            "biggest_risks": {"label": "Eń úlken qáwip", "type": "scalar", "description": "Eń úlken qáwip-qater"},
            "operational_problems": {"label": "Operatsion mashqalalar", "type": "scalar", "description": "Kúndelikli jumıstaǵı mashqalalar"},
            "sales_problems": {"label": "Sawda mashqalaları", "type": "scalar", "description": "Sawdaǵa baylanıslı mashqalalar"},
            "finance_problems": {"label": "Finans mashqalaları", "type": "scalar", "description": "Finansqa baylanıslı mashqalalar"},
        },
    },
}

# ---------------------------------------------------------------------------
# Eski (legacy) maydan atları -> jańa standart atlar. Derek oqılǵanda
# avtomat kóshiriledi (migratsiya), hesh nárse joǵalmaydı.
# ---------------------------------------------------------------------------

LEGACY_FIELD_ALIASES = {
    "customers.avg_check": "sales.average_check",
    "customers.avg_customers_month": "customers.average_monthly_customers",
    "goals.current_goals": "goals.current",
    "goals.goals_3_months": "goals.current",  # "jaqın múddetli" — "current" tusinigine kiredi
    "goals.goals_1_year": "goals.one_year",
    "goals.strategic_goals": "goals.strategic",
}

# ---------------------------------------------------------------------------
# NUMERIC maydanlar ushın ólshem birlikleri (set_numeric_field qara).
# Bul dizimnen tıs ólshem birligi qabıl etilmeydi — ойдан bir nárse
# oylap tabılmaydı, tanılmaǵan birlik ANIQ qátelik beredi.
# ---------------------------------------------------------------------------

NUMERIC_UNITS = {"UZS", "USD", "KZT", "percent", "count"}


def known_field_keys() -> list:
    """Barlıq DURIS (jańa, standart) 'bólim.maydan' kilitleri, tool-schema
    enum ushın. Legacy atlar bul dizimde JOQ — jańa jazıwlar hámishe
    standart maydanǵa túsedi."""
    keys = []
    for section, meta in FIELD_SCHEMA.items():
        for field in meta["fields"]:
            keys.append(f"{section}.{field}")
    return keys


def _field_meta(field_key: str):
    section, _, field = field_key.partition(".")
    meta = FIELD_SCHEMA.get(section)
    if not meta:
        return None
    return meta["fields"].get(field)


def field_label(field_key: str) -> str:
    meta = _field_meta(field_key)
    return meta["label"] if meta else field_key


def field_type(field_key: str) -> str:
    """'scalar' yamasa 'list'. Belgisiz maydan ushın 'scalar' qaytaradı."""
    meta = _field_meta(field_key)
    return meta["type"] if meta else "scalar"


# ---------------------------------------------------------------------------
# Qáwipsiz fayl atı
# ---------------------------------------------------------------------------


def _slugify(name: str) -> str:
    key = kaa.match_key(name)[:40]
    slug = _SLUG_RE.sub("-", key).strip("-")
    return slug or "biznes"


def _business_data_dir(memory_dir: Path) -> Path:
    d = memory_dir / "business_data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _business_path(memory_dir: Path, business_name: str) -> Path:
    return _business_data_dir(memory_dir) / f"{_slugify(business_name)}.json"


# ---------------------------------------------------------------------------
# Legacy migratsiya — derek JOǴALMAYDI, tek jańa kilitke kóshedi
# ---------------------------------------------------------------------------


def _merge_entry(dest: dict, incoming: dict) -> dict:
    """Eki entry (value/updated_at/previous, kerek bolsa unit) kelse,
    jańasın (updated_at úlken) "aǵımdaǵı" etip qaldıradı, eskisin
    "previous" retinde saqlaydı. Hesh bir qıymat joǵalmaydı.

    "unit" — NUMERIC maydanlar ushın ǵana boladı (3-faza); scalar/list
    entry-lerde bul kilt joq, sonıń ushın olarǵa tásir etpeydi."""
    if not dest:
        return incoming
    if not incoming:
        return dest
    newer, older = (dest, incoming) if dest.get("updated_at", "") >= incoming.get("updated_at", "") else (incoming, dest)
    merged = {"value": newer["value"], "updated_at": newer["updated_at"]}
    if "unit" in newer:
        merged["unit"] = newer["unit"]
    if newer.get("previous"):
        prev = newer["previous"]
    else:
        prev = {"value": older.get("value"), "updated_at": older.get("updated_at")}
        if "unit" in older:
            prev["unit"] = older["unit"]
    merged["previous"] = prev
    return merged


def _migrate_legacy_fields(data: dict) -> tuple:
    """Eski bólim.maydan kilitlerin (LEGACY_FIELD_ALIASES) jańasına
    kóshiredi. (data, ózgeris_boldı_ma) qaytaradı."""
    fields = data.get("fields") or {}
    changed = False

    for old_key, new_key in LEGACY_FIELD_ALIASES.items():
        old_section, _, old_field = old_key.partition(".")
        old_section_data = fields.get(old_section)
        if not old_section_data or old_field not in old_section_data:
            continue

        old_entry = old_section_data.pop(old_field)
        if not old_section_data:
            fields.pop(old_section, None)

        new_section, _, new_field = new_key.partition(".")
        new_section_data = fields.setdefault(new_section, {})
        new_section_data[new_field] = _merge_entry(new_section_data.get(new_field), old_entry)
        changed = True

    data["fields"] = fields
    return data, changed


# ---------------------------------------------------------------------------
# Oqıw
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_and_migrate(memory_dir: Path, business_name: str):
    """Fayldı oqıydı, legacy maydanlar bolsa jańasına kóshiredi hám
    (ózgeris bolsa) diskke qayta jazadı — burınǵı fayl .json.bak retinde
    saqlanadı (bir ret, qáwipsizlik ushın)."""
    path = _business_path(memory_dir, business_name)
    if not path.exists():
        return path, None

    raw_text = path.read_text(encoding="utf-8")
    data = json.loads(raw_text) if raw_text.strip() else {}
    data, changed = _migrate_legacy_fields(data)

    if changed:
        backup = path.with_suffix(".json.bak")
        if not backup.exists():
            backup.write_text(raw_text, encoding="utf-8")
        _atomic_write(path, data)

    return path, data


def list_businesses(memory_dir: Path) -> list:
    """Belgili biznes atlarınıń dizimin qaytaradı (business_name maydanınan)."""
    d = memory_dir / "business_data"
    if not d.exists():
        return []
    names = []
    for path in sorted(d.glob("*.json")):
        data = _read_json(path)
        if data:
            names.append(data.get("business_name") or path.stem)
    return names


def load_business(memory_dir: Path, business_name: str):
    """Bir biznestiń tolıq JSON-ın qaytaradı (legacy maydanlar avtomat
    jańa atqa kóshirilgen halda), joq bolsa None."""
    _, data = _load_and_migrate(memory_dir, business_name)
    return data


def find_business_in_text(memory_dir: Path, text: str):
    """Tekstte belgili biznes atı ushırasa, sonıń maǵlıwmatın qaytaradı."""
    text_key = kaa.match_key(text or "")
    if not text_key:
        return None
    for name in list_businesses(memory_dir):
        if kaa.match_key(name) and kaa.match_key(name) in text_key:
            return load_business(memory_dir, name)
    return None


# ---------------------------------------------------------------------------
# Jazıw (TEK usı eki funktsiya arqalı)
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)  # atomik almastırıw — jarım-jasar jazıw bolmaydı


def _load_or_init(memory_dir: Path, business_name: str) -> tuple:
    path, data = _load_and_migrate(memory_dir, business_name)
    now = _dt.datetime.now().isoformat(timespec="seconds")
    if data is None:
        data = {}
    data.setdefault("business_name", business_name)
    data.setdefault("created_at", now)
    data.setdefault("fields", {})
    data.setdefault("notes", [])
    return path, data, now


def set_field(memory_dir: Path, business_name: str, field_key: str, value: str) -> Path:
    """Struktura maydandı jańalaydı. Eski qıymat joǵalmaydı — 'previous'
    retinde saqlanadı (tolıq versiya tariyxı EMES, tek aldınǵısı).

    Eskertiw: type="list" belgilengen maydanlar da (equipment,
    main_products, target_customers, segments, acquisition_channels)
    házirshe usı funktsiya arqalı SCALAR sıyaqlı isleydi — hár jazıw
    eskisin almastıradı, QOSPAYDI. Kóp elementti dizim retinde saqlaw —
    kelesi fazadaǵı append_to_list_field() ushın."""
    if field_key not in known_field_keys():
        raise ValueError(f"belgisiz maydan: {field_key}")
    value = (value or "").strip()
    if not value:
        raise ValueError("qıymat bos boldı")

    path, data, now = _load_or_init(memory_dir, business_name)
    section, _, field = field_key.partition(".")
    section_data = data["fields"].setdefault(section, {})
    existing = section_data.get(field)

    entry = {"value": value, "updated_at": now}
    if existing and existing.get("value") != value:
        entry["previous"] = {"value": existing.get("value"), "updated_at": existing.get("updated_at")}
    elif existing and existing.get("previous"):
        entry["previous"] = existing["previous"]

    section_data[field] = entry
    data["updated_at"] = now
    _atomic_write(path, data)
    return path


def _coerce_numeric(value):
    """`value`-di san (int yamasa float) etip qaytaradı. San BOLMASA
    (parse etilmese, NaN/Infinity bolsa, bool bolsa) — ANIQ ValueError
    shıǵaradı, hesh nárseni "sheshiwge" urınbaydı (mısalı, "100 mln som"
    tekstinen sandı awtomat ajıratıp alıw — bul jerde EMES, tools.py/
    model dárejesinde islenetuǵın jumıs, KELESI faza)."""
    if isinstance(value, bool):
        raise ValueError(f"qıymat numeric emes (bool berildi): {value!r}")
    if isinstance(value, (int, float)):
        num = float(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("numeric qıymat bos boldı")
        try:
            num = float(text)
        except ValueError:
            raise ValueError(f"qıymat numeric emes: '{value}'") from None
    else:
        raise ValueError(f"qıymat numeric emes: {value!r}")

    if not math.isfinite(num):
        raise ValueError(f"qıymat numeric emes (shekli san emes): {value!r}")

    return int(num) if num.is_integer() else num


def set_numeric_field(memory_dir: Path, business_name: str, field_key: str, value, unit: str = None) -> Path:
    """NUMERIC-type maydandı (revenue, cost, gross_margin, fixed_costs,
    cash_flow, monthly_sales, average_check, average_monthly_customers)
    struktura sandı túrde jańalaydı: {"value": <san>, "unit": <birlik>,
    "updated_at": ...}.

    `set_field()`-ten ULKEN parqı: bul funktsiya field_key-diń type-i
    ANIQ "numeric" bolıwın talap etedi (basqasha ValueError), hám `value`
    haqıyqıy sanǵa aylandırıla alıwı kerek (basqasha ValueError — "100
    mln som" sıyaqlı tekst osı jerde qabıl etilmeydi, ol ele parse
    etilmegen tekst, sandı ózi shıǵarıp alıw bul funktsiyanıń jumısı
    EMES).

    `unit` — NUMERIC_UNITS dizimindegi birew boliwı kerek (UZS, USD,
    KZT, percent, count). Berilmese (None yamasa bos qatar) — "unknown"
    etip saqlanadı (bul QÁTE EMES, ANIQ "belgisiz" belgisi). Al berilip,
    biraq dizimde JOQ bolsa — ANIQ ValueError (hesh qashan "eń jaqın"
    birlikke silently aylandırılmaydı).

    Eski qıymat (san yamasa eski tekst-scalar bolsa da) joǵalmaydı —
    "previous" retinde ({"value", "unit", "updated_at"}) saqlanadı, dál
    set_field()-tegidey principte."""
    if field_key not in known_field_keys():
        raise ValueError(f"belgisiz maydan: {field_key}")
    if field_type(field_key) != "numeric":
        raise ValueError(
            f"'{field_key}' NUMERIC maydan emes (type={field_type(field_key)!r}) — "
            "set_numeric_field ushın jaramsız, set_field() qollan"
        )

    numeric_value = _coerce_numeric(value)

    if unit is None:
        unit = "unknown"
    else:
        if not isinstance(unit, str):
            raise ValueError(f"ólshem birligi tekst bolıwı kerek: {unit!r}")
        unit = unit.strip()
        if not unit:
            unit = "unknown"
        elif unit not in NUMERIC_UNITS:
            raise ValueError(
                f"belgisiz ólshem birligi: '{unit}' — bilinetuǵınlar: "
                f"{', '.join(sorted(NUMERIC_UNITS))} (yamasa qaldırıp 'unknown' etiw múmkin)"
            )

    path, data, now = _load_or_init(memory_dir, business_name)
    section, _, field = field_key.partition(".")
    section_data = data["fields"].setdefault(section, {})
    existing = section_data.get(field)

    entry = {"value": numeric_value, "unit": unit, "updated_at": now}
    if existing:
        existing_value = existing.get("value")
        existing_unit = existing.get("unit", "unknown")
        if existing_value != numeric_value or existing_unit != unit:
            entry["previous"] = {
                "value": existing_value,
                "unit": existing_unit,
                "updated_at": existing.get("updated_at"),
            }
        elif existing.get("previous"):
            entry["previous"] = existing["previous"]

    section_data[field] = entry
    data["updated_at"] = now
    _atomic_write(path, data)
    return path


def _dedupe_preserve_order(values) -> list:
    """Dublikatlardı alıp taslaydı (kaa.casefold + strip — MINIMAL
    normalizatsiya, tek qásiyetsiz parıqlar ushın), birinshi ushırasqan
    original jazılıwın saqlaydı. None/bos qatarlar ótkerip jiberiledi."""
    seen = set()
    result = []
    for v in values:
        if not isinstance(v, str):
            continue
        v = v.strip()
        if not v:
            continue
        key = kaa.casefold(v)
        if key in seen:
            continue
        seen.add(key)
        result.append(v)
    return result


def append_to_list_field(memory_dir: Path, business_name: str, field_key: str, value: str) -> Path:
    """LIST-type maydanǵa jańa element QOSADI — bar elementlerdi hesh
    qashan almastırmaydı. `set_field()`-ten parqı: bul jerde 'previous'
    mexanizmi QOLLANILMAYDI (list-tiń ózi — aǵımdaǵı jıynaq, tariyx
    emes; 9-tarawdı qara).

    Eski maǵlıwmattı JOǴALTPAW principi:
      - Eger maydan búrın SCALAR (Fasa-1-den qalǵan bir qatar) bolsa,
        ol avtomat birinshi element etip alınadı.
      - Eger sonıń "previous"-i de bar bolsa (SCALAR bolǵanda `set_field`
        arqalı jazılǵan aldınǵı nusqa), ol da dizimge kiredi — hesh bir
        tariyxıy qıymat joǵalmaydı, tek endi bólek elementler retinde.
      - Qaytalanǵan qıymat (bos orın/úlken-kishi hárip parqı esapqa
        alınbay) ekinshi ret qosılmaydı — birinshi ushırasqan jazılıwı
        saqlanadı.
    """
    if field_key not in known_field_keys():
        raise ValueError(f"belgisiz maydan: {field_key}")
    if field_type(field_key) != "list":
        raise ValueError(f"'{field_key}' LIST maydan emes (type=scalar) — append_to_list_field ushın jaramsız")

    value = (value or "").strip()
    if not value:
        raise ValueError("qosılatuǵın qıymat bos boldı")

    path, data, now = _load_or_init(memory_dir, business_name)
    section, _, field = field_key.partition(".")
    section_data = data["fields"].setdefault(section, {})
    existing = section_data.get(field)

    pool = []
    if existing:
        old_value = existing.get("value")
        if isinstance(old_value, list):
            pool.extend(old_value)
        elif isinstance(old_value, str):
            pool.append(old_value)
        prev = existing.get("previous") or {}
        prev_value = prev.get("value")
        if isinstance(prev_value, list):
            pool.extend(prev_value)
        elif isinstance(prev_value, str):
            pool.append(prev_value)
    pool.append(value)

    items = _dedupe_preserve_order(pool)

    # LIST maydan ushın "previous" jazılmaydı — eski entry-de bar bolsa da
    # taslanadı (endi barlıq tariyxıy qıymatlar items ishinde saqlanǵan).
    section_data[field] = {"value": items, "updated_at": now}
    data["updated_at"] = now
    _atomic_write(path, data)
    return path


def add_knowledge_note(memory_dir: Path, business_name: str, text: str) -> Path:
    """Struktura maydanǵa sıymaytuǵın erkin fakttı (BUSINESS KNOWLEDGE)
    sol biznestiń jazbasına qosadı."""
    text = (text or "").strip()
    if not text:
        raise ValueError("tekst bos boldı")

    path, data, now = _load_or_init(memory_dir, business_name)
    data["notes"].append({"text": text, "added_at": now})
    data["updated_at"] = now
    _atomic_write(path, data)
    return path


# ---------------------------------------------------------------------------
# Qısqasha kórsetiw (search_brain ushın)
# ---------------------------------------------------------------------------


def format_business_summary(data: dict, max_notes: int = 5) -> str:
    """Bar maǵlıwmattı qısqasha jazba etip beredi — JOQ maydandı hesh
    qashan oylap tappaydı, tek 'belgisiz' dep ataydı."""
    if not data:
        return "Bul biznes haqqında hesh qanday maǵlıwmat joq."

    lines = [f"# {data.get('business_name', '?')}"]
    empty_sections = []

    for section, meta in FIELD_SCHEMA.items():
        section_data = (data.get("fields") or {}).get(section) or {}
        if not section_data:
            empty_sections.append(meta["label"])
            continue
        lines.append(f"\n## {meta['label']}")
        for field, field_meta in meta["fields"].items():
            entry = section_data.get(field)
            if not entry:
                continue
            raw_value = entry.get("value")
            if isinstance(raw_value, list):
                shown = "; ".join(raw_value)
            elif "unit" in entry:
                unit = entry.get("unit") or "unknown"
                shown = f"{raw_value} ({unit})" if unit != "unknown" else f"{raw_value} (ólshem birligi belgisiz)"
            else:
                shown = raw_value
            lines.append(f"- {field_meta['label']}: {shown} (jańalanǵan: {entry.get('updated_at', '?')[:10]})")

    notes = data.get("notes") or []
    if notes:
        lines.append("\n## Basqa jazbalar (business knowledge)")
        for note in notes[-max_notes:]:
            lines.append(f"- {note.get('text')} ({note.get('added_at', '?')[:10]})")

    if empty_sections:
        lines.append("\n## Belgisiz (fayllarda joq)")
        lines.append(", ".join(empty_sections))

    return "\n".join(lines)
