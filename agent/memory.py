"""
memory.py — Jarvis-tiń emin-erkin jaza alatuǵın JALǴIZ jeri: memory/.

Basqa hesh bir fayl memory/ papkasına tikkeley jazbaydı — bári usı modul
arqalı ótedi. Bul "Jarvis nendey jazǵan?" degen soraqqa juwaptı bir jerden
tabıwǵa múmkinshilik beredi hám qaǵıyda #3-ti (memory/ ge jazǵanıńdı
hámishe dawıs penen aytasań) tekseriwdi ańsatlastıradı.
"""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path

import kaa

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    key = kaa.match_key(text)[:40]
    slug = _SLUG_RE.sub("-", key).strip("-")
    return slug or "jazba"


def write(memory_dir: Path, fact: str) -> Path:
    """
    Bir faktti sánelengen .md faylına jazadı, jazılǵan fayl jolın qaytaradı.
    Fayl atı hámishe búgingi sáne menen baslanadı, sonıń ushın memory/
    papkasınıń ózi de dawırnama (xronologiya) bolıp qaladı.
    """
    fact = (fact or "").strip()
    if not fact:
        raise ValueError("Saqlanatuǵın tekst bos boldı")

    memory_dir.mkdir(parents=True, exist_ok=True)
    today = _dt.date.today().isoformat()
    slug = _slugify(fact)
    path = memory_dir / f"{today}-{slug}.md"
    n = 2
    while path.exists():
        path = memory_dir / f"{today}-{slug}-{n}.md"
        n += 1

    path.write_text(f"# {today}\n\n{fact}\n", encoding="utf-8")
    return path


def list_recent(memory_dir: Path, limit: int = 5) -> list:
    """Sońǵı jazılǵan yad fayllarınıń qısqasha dizimin qaytaradı."""
    if not memory_dir.exists():
        return []
    files = sorted(memory_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"file": f.name, "text": f.read_text(encoding="utf-8")[:300]} for f in files[:limit]]


def read_all(memory_dir: Path) -> list:
    """Barlıq yad jazbalardı tolıq qaytaradı (brief_me hám sáwbet konteksti ushın)."""
    if not memory_dir.exists():
        return []
    files = sorted(memory_dir.glob("*.md"))
    return [{"file": f.name, "text": f.read_text(encoding="utf-8")} for f in files]
