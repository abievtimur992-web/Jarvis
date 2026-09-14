"""
tools.py — Jarvis-tiń "hámmesi qosılǵan" bes quralı:
search_brain, research_web, remember, plan_day, brief_me.

Hár bir tool EKI nárse qaytaradı:
  spoken — dawısqa aytılatuǵın qısqa gáp (1-2 sóylem), ekranǵa shıǵarılmaydı
  card   — ekranǵa shıǵarılatuǵın tolıq, naqtı maǵlıwmat (dict)

Bul eki nárse hesh qashan bir-birinen kóshirilmeydi: spoken — qısqa juwmaq,
card — tekseriwge boladurǵan tolıq maǵlıwmat (fayl atları, sanlar h.t.b.).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import kaa
import memory as memory_mod
import vault as vault_mod

# ---------------------------------------------------------------------------
# 1) search_brain — jazbalardan naqtı fakt izlew
# ---------------------------------------------------------------------------


def search_brain(v: vault_mod.Vault, query: str) -> dict:
    results = vault_mod.search(v, query, limit=5)
    if not results:
        return {
            "spoken": f'"{query}" haqqında jazbalarda hesh nárse tabılmadı.',
            "card": {"tool": "search_brain", "query": query, "results": []},
        }

    titles = [n.title for n, _ in results[:3]]
    if len(results) == 1:
        spoken = f"{titles[0]} jazbasında taptım."
    else:
        spoken = f"{len(results)} jazbada taptım: {', '.join(titles)}."

    return {
        "spoken": spoken,
        "card": {
            "tool": "search_brain",
            "query": query,
            "results": [
                {
                    "title": n.title,
                    "type": n.note_type,
                    "path": n.rel_path,
                    "excerpt": n.text[:500],
                }
                for n, _ in results
            ],
        },
    }


# ---------------------------------------------------------------------------
# 2) research_web — internetten izlew, soń óz bahalarına "qondırıw"
# ---------------------------------------------------------------------------


def _duckduckgo_lookup(query: str):
    """Kilitsiz, ápiwayı internet izlew (DuckDuckGo Instant Answer). Internet
    joq yamasa bloklanǵan bolsa — None qaytaradı, qátelik shıǵarmaydı."""
    try:
        url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(
            {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Jarvis/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data.get("AbstractText") or ""
        if not text and data.get("RelatedTopics"):
            first = data["RelatedTopics"][0]
            if isinstance(first, dict):
                text = first.get("Text", "")
        return text or None
    except Exception:
        return None


def research_web(query: str, profile: dict) -> dict:
    web_answer = _duckduckgo_lookup(query)
    lines = []
    if web_answer:
        lines.append(f"Internetten tabılǵanı: {web_answer}")
    else:
        lines.append(
            "Internetten juwap tabılmadı (internet joq yamasa Jarvis izlewge erise almadı)."
        )

    price_lines = []
    for b in (profile or {}).get("businesses", []):
        for key, val in (b.get("prices") or {}).items():
            if key != "note":
                price_lines.append(f"{b.get('brand')}: {key} — {val}")
    if price_lines:
        lines.append("Seniń óz bahalarıń (fayllardan): " + "; ".join(price_lines))
    else:
        lines.append("Seniń óz bahalarıń bul tema boyınsha fayllarda belgisiz.")

    if web_answer:
        spoken = f"Taptım: {web_answer[:140]}. Óziniń bahalarıńdı da kártaǵa qostım."
    else:
        spoken = "Internetten juwap tabılmadı, biraq óziniń bahalarıńdı kártaǵa qostım."

    return {
        "spoken": spoken,
        "card": {
            "tool": "research_web",
            "query": query,
            "web_answer": web_answer,
            "lines": lines,
        },
    }


# ---------------------------------------------------------------------------
# 3) remember — bir fakt, bir sánelengen fayl (memory.py arqalı — jalgız jazıwshı)
# ---------------------------------------------------------------------------


def remember(memory_dir: Path, fact: str) -> dict:
    fact = (fact or "").strip()
    if not fact:
        return {
            "spoken": "Ne este saqlaw kerekligin túsinbedim, qayta aytıp ber.",
            "card": {"tool": "remember", "file": None, "text": ""},
        }

    path = memory_mod.write(memory_dir, fact)

    return {
        "spoken": f'Jazıp qoydım: "{fact}" — {path.name} faylına.',
        "card": {"tool": "remember", "file": path.name, "text": fact},
    }


# ---------------------------------------------------------------------------
# 4) plan_day — búgingi eń kóp aqsha ózgeretuǵın 5 is
# ---------------------------------------------------------------------------


def plan_day(v: vault_mod.Vault, profile: dict) -> dict:
    items: list[str] = []

    problem = ((profile or {}).get("finance") or {}).get("biggest_problem")
    if problem:
        items.append(f"Finans: {problem.split('—')[0].strip()}")

    for note in v.notes.values():
        if len(items) >= 5:
            break
        if "mashqala" in kaa.match_key(note.title):
            for line in note.text.splitlines():
                line = line.strip("-* \t")
                if not line or line.startswith("#"):
                    continue
                if kaa.match_key(line).startswith("baylanisli"):
                    continue
                if line not in items and len(items) < 5:
                    items.append(line[:120])

    for g in (profile or {}).get("goals_3_months", []):
        if len(items) >= 5:
            break
        if g not in items:
            items.append(g)

    items = items[:5]
    if not items:
        return {
            "spoken": "Búgin ushın naqtı joba tabılmadı — fayllarǵa mashqala yamasa maqset qos.",
            "card": {"tool": "plan_day", "items": []},
        }

    spoken = f"Búgingi jobada {len(items)} tarmaq bar. Birinshisi: {items[0][:80]}."
    return {"spoken": spoken, "card": {"tool": "plan_day", "items": items}}


# ---------------------------------------------------------------------------
# 5) brief_me — ne qaldı, ne kelesi (jazba + yad boyınsha)
# ---------------------------------------------------------------------------


def brief_me(v: vault_mod.Vault, memory_dir: Path) -> dict:
    recent_memory = memory_mod.list_recent(memory_dir, limit=5)

    kundelik_notes = [n for n in v.notes.values() if kaa.match_key(n.note_type) == kaa.match_key("kundelik")]
    kundelik_notes.sort(key=lambda n: n.rel_path, reverse=True)
    recent_notes = [{"title": n.title, "excerpt": n.text[:300]} for n in kundelik_notes[:3]]

    parts = []
    if recent_notes:
        parts.append(f"Kúndelik jazbalarda {len(recent_notes)} jańalıq bar.")
    if recent_memory:
        parts.append(f"Yadda {len(recent_memory)} jazba saqlanǵan.")
    if not parts:
        parts.append("Ele jańalıq yamasa yad jazba joq.")

    return {
        "spoken": " ".join(parts),
        "card": {"tool": "brief_me", "recent_notes": recent_notes, "recent_memory": recent_memory},
    }


# ---------------------------------------------------------------------------
# Anthropic tool-schema-ları hám dispetcher
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "search_brain",
        "description": (
            "Iyeniń jazbalarınan (klientler, ónimler, bahalar, mashqalalar, maqsetler) "
            "naqtı bir faktti izlew. Hámishe qaysı fayldan tabılǵanın atap ótiw kerek."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Izlenetuǵın soraw"}},
            "required": ["query"],
        },
    },
    {
        "name": "research_web",
        "description": (
            "Internetten bir nárseni izlep, soń nátiyjeni iyeniń óz bahaları menen "
            "salıstırıw (som penen). Iyeniń bahası belgisiz bolsa, sonı ashıq aytıw kerek."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Internetten izlenetuǵın soraw"}},
            "required": ["query"],
        },
    },
    {
        "name": "remember",
        "description": (
            "Bir faktti memory/ papkasına sánelengen fayl etip jazıp qoyıw. Tek iye "
            "ózi 'esimde saqla' dep sorasa yamasa aytqanı 3 aydan keyin de kerek boliwı "
            "mumkin bolǵanda qollanıladı."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"fact": {"type": "string", "description": "Saqlanatuǵın bir fakt, qısqa gápte"}},
            "required": ["fact"],
        },
    },
    {
        "name": "plan_day",
        "description": "Búgingi kún ushın eń kóp 5 istiń dizimin dúziw, aqshaǵa eń kóp tásir etetuǵınnan baslap.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "brief_me",
        "description": "Ne qalǵanın hám kelesi ne kerekligin jazbalar hám yad boyınsha qısqasha aytıw.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def run_tool(name: str, tool_input: dict, ctx: dict) -> dict:
    """
    ctx: {"vault": Vault, "profile": dict, "memory_dir": Path}
    Qaytaradı: {"spoken": str, "card": dict}
    """
    v = ctx["vault"]
    profile = ctx.get("profile") or {}
    memory_dir = ctx["memory_dir"]

    if name == "search_brain":
        return search_brain(v, tool_input.get("query", ""))
    if name == "research_web":
        return research_web(tool_input.get("query", ""), profile)
    if name == "remember":
        return remember(memory_dir, tool_input.get("fact", ""))
    if name == "plan_day":
        return plan_day(v, profile)
    if name == "brief_me":
        return brief_me(v, memory_dir)

    return {
        "spoken": f"Bunday qural joq: {name}.",
        "card": {"tool": name, "error": "belgisiz tool"},
    }
