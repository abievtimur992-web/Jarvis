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
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
from pathlib import Path

import kaa

_SLUG_RE = re.compile(r"[^a-z0-9]+")

# ---------------------------------------------------------------------------
# Onboarding sxeması (Timur soraǵan A-H bólimleri)
# ---------------------------------------------------------------------------

FIELD_SCHEMA = {
    "identity": {
        "label": "Biznes tuwralı",
        "fields": {
            "business_type": "Biznes túri",
            "location": "Jaylasqan jeri",
            "years_operating": "Neshe jıldan beri isleydi",
            "owner": "Iyesi",
            "employees": "Xızmetkerler sanı",
        },
    },
    "products": {
        "label": "Ónimler/xızmetler",
        "fields": {
            "categories": "Ónim kategoriyaları",
            "main_products": "Tiykarǵı ónimler",
            "services": "Xızmetler",
            "production_capabilities": "Islep shıǵarıw múmkinshiligi",
            "equipment": "Úskene",
        },
    },
    "customers": {
        "label": "Klientler",
        "fields": {
            "target_customers": "Maqsetli klientler",
            "segments": "Klient segmentleri",
            "avg_customers_month": "Aylıq ortasha klient sanı",
            "repeat_customers": "Qayta kelgen klientler",
            "avg_check": "Ortasha chek",
        },
    },
    "sales": {
        "label": "Sawda",
        "fields": {
            "monthly_sales": "Aylıq sawda",
            "channels": "Sawda kanalları",
            "seasonality": "Mawsımlıq",
            "conversion": "Konversiya",
            "leads": "Leadlar",
        },
    },
    "finance": {
        "label": "Finans",
        "fields": {
            "revenue": "Kirim",
            "cost": "Shıǵın",
            "gross_margin": "Jalpı marja",
            "fixed_costs": "Turaqlı shıǵınlar",
            "debts": "Qarızlar",
            "investments": "Investitsiyalar",
            "cash_flow": "Aqsha aǵımı",
        },
    },
    "marketing": {
        "label": "Marketing",
        "fields": {
            "instagram": "Instagram",
            "telegram": "Telegram",
            "advertising": "Reklama",
            "acquisition_channels": "Klient tabıw kanalları",
            "competitors": "Baseketlesler",
        },
    },
    "goals": {
        "label": "Maqsetler",
        "fields": {
            "current_goals": "Házirgi maqsetler",
            "goals_3_months": "3 aylıq maqsetler",
            "goals_1_year": "1 jıllıq maqsetler",
            "strategic_goals": "Strategiyalıq maqsetler",
        },
    },
    "problems": {
        "label": "Mashqalalar",
        "fields": {
            "bottlenecks": "Tarlawıq jerler",
            "biggest_risks": "Eń úlken qáwip",
            "operational_problems": "Operatsion mashqalalar",
            "sales_problems": "Sawda mashqalaları",
            "finance_problems": "Finans mashqalaları",
        },
    },
}


def known_field_keys() -> list:
    """Barlıq durıs 'bólim.maydan' kilitleri, tool-schema enum ushın."""
    keys = []
    for section, meta in FIELD_SCHEMA.items():
        for field in meta["fields"]:
            keys.append(f"{section}.{field}")
    return keys


def field_label(field_key: str) -> str:
    section, _, field = field_key.partition(".")
    meta = FIELD_SCHEMA.get(section)
    if not meta:
        return field_key
    return meta["fields"].get(field, field_key)


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
# Oqıw
# ---------------------------------------------------------------------------


def list_businesses(memory_dir: Path) -> list:
    """Belgili biznes atlarınıń dizimin qaytaradı (business_name maydanınan)."""
    d = memory_dir / "business_data"
    if not d.exists():
        return []
    names = []
    for path in sorted(d.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            names.append(data.get("business_name") or path.stem)
        except Exception:
            continue
    return names


def load_business(memory_dir: Path, business_name: str):
    """Bir biznestiń tolıq JSON-ın qaytaradı, joq bolsa None."""
    path = _business_path(memory_dir, business_name)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


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
    path = _business_path(memory_dir, business_name)
    now = _dt.datetime.now().isoformat(timespec="seconds")
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}
    data.setdefault("business_name", business_name)
    data.setdefault("created_at", now)
    data.setdefault("fields", {})
    data.setdefault("notes", [])
    return path, data, now


def set_field(memory_dir: Path, business_name: str, field_key: str, value: str) -> Path:
    """Struktura maydandı jańalaydı. Eski qıymat joǵalmaydı — 'previous'
    retinde saqlanadı (tolıq versiya tariyxı EMES, tek aldınǵısı)."""
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
        for field, label in meta["fields"].items():
            entry = section_data.get(field)
            if entry:
                lines.append(f"- {label}: {entry.get('value')} (jańalanǵan: {entry.get('updated_at', '?')[:10]})")

    notes = data.get("notes") or []
    if notes:
        lines.append("\n## Basqa jazbalar (business knowledge)")
        for note in notes[-max_notes:]:
            lines.append(f"- {note.get('text')} ({note.get('added_at', '?')[:10]})")

    if empty_sections:
        lines.append("\n## Belgisiz (fayllarda joq)")
        lines.append(", ".join(empty_sections))

    return "\n".join(lines)
