"""
vault.py — papkalardı izlenetuǵın grafikke aylandıradı.

Bul fayl Timurdıń papkalarındaǵı .md, .txt hám .pdf fayllardı oqıydı,
[[wikilink]] silteme lerdi grafiktiń qırları (edges) etip aladı, hám izlew
ushın kishi indeks quradı. TEK OQIYDI — hesh nárseni jazbaydı, ózgertpeydi.

Iske túsiriw (test ushın): python vault.py [papka1] [papka2] ...
Argument berilmese, ../biznes papkasın oqıydı.
"""

from __future__ import annotations

import os
import re
import sys
import zlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import kaa

EXCLUDE_DIRS = {"node_modules", ".git", "__pycache__", ".idea", ".vscode"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB — bunnan úlken fayllardı ótkeremiz
TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}
PDF_EXTENSIONS = {".pdf"}

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")
HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

# Til anıqlaw ushın belgi háripler
KAA_LATIN_MARKS = set("áǵńóúıÁǴŃÓÚ")
KAA_CYRILLIC_MARKS = set("әғқңөүўҳӘҒҚҢӨҮЎҲ")
UZBEK_APOSTROPHE_HINTS = ("o'", "g'", "O'", "G'", "ʻ", "ʼ")


# ---------------------------------------------------------------------------
# Maǵlıwmat túrleri
# ---------------------------------------------------------------------------

@dataclass
class Note:
    id: str
    title: str
    path: Path
    rel_path: str
    note_type: str
    text: str
    language: str
    links: list = field(default_factory=list)       # jazbadan shıǵatuǵın siltemeler (tekst)
    backlinks: list = field(default_factory=list)    # bul jazbaǵa kiretuǵın basqa jazba id-leri
    ext: str = ""


@dataclass
class Vault:
    notes: dict = field(default_factory=dict)                 # note_id -> Note
    edges: list = field(default_factory=list)                 # (src_id, dst_id)
    index: dict = field(default_factory=lambda: defaultdict(set))  # stem -> {note_id}
    roots: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    fallback_files: list = field(default_factory=list)        # cp1251 penen oqılǵanlar

    def hub_counts(self) -> Counter:
        c: Counter = Counter()
        for src, dst in self.edges:
            c[src] += 1
            c[dst] += 1
        return c

    def top_hubs(self, n: int = 10):
        counts = self.hub_counts()
        ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        out = []
        for note_id, cnt in ranked[:n]:
            note = self.notes.get(note_id)
            if note:
                out.append((note.title, cnt))
        return out


# ---------------------------------------------------------------------------
# Fayl oqıw
# ---------------------------------------------------------------------------

def _iter_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDE_DIRS and not d.startswith(".")
        ]
        for fname in filenames:
            p = Path(dirpath) / fname
            ext = p.suffix.lower()
            if ext not in TEXT_EXTENSIONS and ext not in PDF_EXTENSIONS:
                continue
            try:
                if p.stat().st_size > MAX_FILE_SIZE:
                    continue
            except OSError:
                continue
            yield p


def _read_text(path: Path, vault: Vault) -> str:
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("cp1251")
            vault.fallback_files.append(str(path))
            return text
        except UnicodeDecodeError:
            return raw.decode("utf-8", errors="replace")


def _extract_pdf_text(path: Path) -> str:
    """
    Júdá jinishke, tek Python-diń óz kitapxanası (zlib, re) penen islenetuǵın
    PDF oqıwshı. Qarapayım PDF-lerde tekstti tabadı; skanerlengen súwretli
    yamasa kúrdeli kódlanǵan PDF-lerde bos qaytarıwı múmkin — bul qátelik
    emes, tek "bul faylda tekst tabılmadı" degeni.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return ""

    texts = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.DOTALL):
        chunk = m.group(1)
        try:
            decompressed = zlib.decompress(chunk)
        except Exception:
            continue
        for tm in re.finditer(rb"\((?:[^()\\]|\\.)*\)", decompressed, re.DOTALL):
            piece = tm.group(0)[1:-1]
            piece = (
                piece.replace(rb"\(", b"(")
                .replace(rb"\)", b")")
                .replace(rb"\\", b"\\")
            )
            try:
                texts.append(piece.decode("latin-1"))
            except Exception:
                continue
    return " ".join(texts)


def _detect_language(text: str) -> str:
    sample = text[:2000]
    if not sample.strip():
        return "belgisiz"

    total_letters = sum(1 for ch in sample if ch.isalpha())
    if total_letters == 0:
        return "belgisiz"

    cyr_count = sum(1 for ch in sample if "Ѐ" <= ch <= "ӿ")

    if cyr_count / total_letters > 0.3:
        if any(ch in KAA_CYRILLIC_MARKS for ch in sample):
            return "qaraqalpaqsha (kirill)"
        if any(ch in "ъэЪЭ" for ch in sample):
            return "orıssha"
        return "kirill (til anıq emes)"

    if any(ch in KAA_LATIN_MARKS for ch in sample):
        return "qaraqalpaqsha (latın)"
    if any(hint in sample for hint in UZBEK_APOSTROPHE_HINTS):
        return "ózbekshe (latın)"
    return "latın (til anıq emes)"


def _note_type_from_path(rel_path: str) -> str:
    parts = Path(rel_path).parts
    if len(parts) > 1:
        return parts[0]
    return "jazba"


def _extract_title(text: str, fallback: str) -> str:
    m = HEADING_RE.search(text)
    if m:
        return m.group(1).strip()
    return fallback


def _tokenize(text: str):
    for m in WORD_RE.finditer(text):
        yield m.group(0)


# ---------------------------------------------------------------------------
# Grafik qurıw
# ---------------------------------------------------------------------------

def load_vault(paths) -> Vault:
    """Berilgen papka/fayl jollarınan Vault (grafik + indeks) quradı."""
    vault = Vault()
    by_title_key: dict = {}

    for raw_path in paths:
        root = Path(raw_path).expanduser()
        if not root.exists():
            vault.skipped.append(str(root))
            continue
        vault.roots.append(root)
        files = [root] if root.is_file() else list(_iter_files(root))

        for path in files:
            ext = path.suffix.lower()
            try:
                rel = str(path.relative_to(root if root.is_dir() else root.parent))
            except ValueError:
                rel = path.name

            if ext in PDF_EXTENSIONS:
                text = _extract_pdf_text(path)
            else:
                text = _read_text(path, vault)

            title = _extract_title(text, fallback=path.stem)
            note_id = f"{root.name}/{rel}"
            note = Note(
                id=note_id,
                title=title,
                path=path,
                rel_path=rel,
                note_type=_note_type_from_path(rel),
                text=text,
                language=_detect_language(text),
                ext=ext,
            )
            vault.notes[note_id] = note

            # Sılteme izlew eki kilt penen isleydi: fayl atı hám jazba taqırıbı
            by_title_key[kaa.match_key(path.stem)] = note_id
            by_title_key[kaa.match_key(title)] = note_id

            for token in _tokenize(text):
                stemmed = kaa.stem(kaa.match_key(token))
                if len(stemmed) >= 3:
                    vault.index[stemmed].add(note_id)

    # Eki-jol: barlıq jazba oqılıp bolǵannan soń ǵana siltemelerdi sheshemiz
    for note in vault.notes.values():
        for m in WIKILINK_RE.finditer(note.text):
            target_title = m.group(1).strip()
            note.links.append(target_title)
            target_id = by_title_key.get(kaa.match_key(target_title))
            if target_id and target_id != note.id:
                vault.edges.append((note.id, target_id))
                vault.notes[target_id].backlinks.append(note.id)

    return vault


# ---------------------------------------------------------------------------
# Izlew
# ---------------------------------------------------------------------------

def search(vault: Vault, query: str, limit: int = 5):
    """Sorawǵa eń jaqın jazbalardı qaytaradı: [(Note, score), ...]"""
    tokens = [kaa.stem(kaa.match_key(t)) for t in _tokenize(query)]
    tokens = [t for t in tokens if len(t) >= 2]
    if not tokens:
        return []

    scores: Counter = Counter()
    for token in tokens:
        for note_id in vault.index.get(token, ()):
            scores[note_id] += 1

    for note in vault.notes.values():
        title_key = kaa.match_key(note.title)
        for token in tokens:
            if token in title_key:
                scores[note.id] += 3

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [(vault.notes[nid], score) for nid, score in ranked[:limit]]


# ---------------------------------------------------------------------------
# Esabat (Step 1 ushın: sanlardı ekranǵa shıǵarıw)
# ---------------------------------------------------------------------------

def print_index_report(vault: Vault) -> None:
    print(f"Jámi jazbalar: {len(vault.notes)}")

    by_type = Counter(n.note_type for n in vault.notes.values())
    print("\nTúri boyınsha:")
    for t, c in by_type.most_common():
        print(f"  {t}: {c}")

    by_lang = Counter(n.language for n in vault.notes.values())
    print("\nTil boyınsha:")
    for lang, c in by_lang.most_common():
        print(f"  {lang}: {c}")

    print("\nEń kóp baylanısqan (top 10):")
    hubs = vault.top_hubs(10)
    if not hubs:
        print("  (ele baylanıs joq)")
    for title, cnt in hubs:
        print(f"  {title}: {cnt} baylanıs")

    if vault.fallback_files:
        print(f"\ncp1251 kodirovka menen oqılǵan fayllar ({len(vault.fallback_files)}):")
        for f in vault.fallback_files[:10]:
            print(f"  {f}")

    if vault.skipped:
        print(f"\nTabılmaǵan jollar: {vault.skipped}")


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    default_root = Path(__file__).resolve().parent.parent / "biznes"
    target_paths = sys.argv[1:] or [str(default_root)]
    v = load_vault(target_paths)
    print_index_report(v)
