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
import math
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import business as business_mod
import instagram as instagram_mod
import kaa
import memory as memory_mod
import vault as vault_mod

# ---------------------------------------------------------------------------
# 1) search_brain — jazbalardan naqtı fakt izlew
# ---------------------------------------------------------------------------


def search_brain(v: vault_mod.Vault, query: str, memory_dir: Path) -> dict:
    results = vault_mod.search(v, query, limit=5)

    # BUSINESS DATA/KNOWLEDGE (memory/business_data/*.json) — sorawda belgili
    # biznes atı ushırasa, oniń struktura maydanları hám erkin jazbaları da
    # qosıladı. Bul — PERSONAL MEMORY (memory.py-diń dúz fayllari) EMES,
    # bólek saqlanadı (business.py qara).
    business_data = business_mod.find_business_in_text(memory_dir, query)
    business_summary = business_mod.format_business_summary(business_data) if business_data else None

    if not results and not business_summary:
        return {
            "spoken": f'"{query}" haqqında jazbalarda hesh nárse tabılmadı.',
            "card": {"tool": "search_brain", "query": query, "results": [], "business": None},
        }

    titles = [n.title for n, _ in results[:3]]
    if len(results) == 1:
        spoken = f"{titles[0]} jazbasında taptım."
    elif results:
        spoken = f"{len(results)} jazbada taptım: {', '.join(titles)}."
    else:
        spoken = ""
    if business_summary:
        biz_line = f"{business_data.get('business_name')} haqqında biznes maǵlıwmatın da taptım."
        spoken = f"{spoken} {biz_line}".strip() if spoken else biz_line

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
            "business": business_summary,
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
#
# NUMERIC integratsiya (BUSINESS DECISION ENGINE 3-basqısh): `value`+`unit`
# berilse, san model TÁREPINEN ALDIN parse etilgen dep esaplanadı — bul
# funktsiya "20 mln som" sıyaqlı tekstten sandı ÓZI ajıratıp almaydı (bul
# — model/prompt.md dárejesindegi jumıs, set_numeric_field()-tiń óz
# dokstringinde de aytılǵanday). `value` berilmese, EMES ÓZGERISSIZ eski
# jol (set_field, tekst) isleydi — tolıq keri sáykes.

# Bul dizimdegi maydanlar ushın ǵana teris (negative) san qabıllanadı —
# marja hám aqsha aǵımı teris boliwı múmkin (zıyan, shıǵın), al kirim/
# shıǵın/sawda/klient sanı hesh qashan teris bolmaydı.
_NEGATIVE_ALLOWED_FIELDS = {"finance.gross_margin", "finance.cash_flow"}


def remember(
    memory_dir: Path,
    fact: str,
    business: str = "",
    field: str = "",
    append: bool = False,
    value=None,
    unit: str = None,
) -> dict:
    """
    Tórt jol menen jazadı (bir-birinen bólek saqlanadı, business.py qara):
      0) business + field + value (san, None EMES) berilse hám field
         type="numeric" bolsa — STRUKTURA SANDI maǵlıwmat
         (business_mod.set_numeric_field; value+unit, unit joq bolsa
         "unknown"). Bul EŃ JOQARI basımlıqtaǵı jol — `value` berilse,
         tómendegi 1-jol (tekst) qaraqlanbaydı. `value` san emes yamasa
         field numeric emes yamasa teris san bul maydanǵa ruqsat
         etilmegen bolsa — ANIQ qátelik qaytadı, hesh nárse jazılmaydı.
      1) business + field ekewi de berilse hám field durıs bolsa (yamasa
         `value` berilmegen bolsa) — BUSINESS DATA (struktura maydan,
         memory/business_data/<biznes>.json).
         - append=True HÁM field type="list" bolsa — bar dizimge JAŃA
           element QOSADI (business_mod.append_to_list_field; dublikattı
           óziniń ishinde biykarlaydı — bul jerde qaytalanbaydı).
         - basqa jaǵdayda (append=False, yamasa append=True biraq field
           SCALAR bolsa) — burıngıday set_field (JAŃALAW/ALMASTIRIW,
           eskisi "aldınǵısı" retinde saqlanadı). Yaǵnıy append=True
           scalar maydanda QÁTE bermeydi, tek biykarlanıp set_field-ke
           ótedi ("safe fallback").
      2) tek business berilse (yamasa field durıs bolmasa) — BUSINESS
         KNOWLEDGE (sol biznestiń erkin jazba bólimi).
      3) hesh qaysısı berilmese — burıngıday PERSONAL MEMORY
         (memory/<sáne>-<slug>.md, memory.py arqalı). append parametri
         bul jolǵa hesh tásir etpeydi.
    """
    if business and field and value is not None:
        field_t = business_mod.field_type(field)
        if field_t != "numeric":
            message = f"'{field}' numeric maydan emes (type={field_t!r}) — sandı bul maydanǵa jazıw múmkin emes."
            return {
                "spoken": f"Jaza almadım: {message}",
                "card": {
                    "tool": "remember", "kind": "business_data", "operation": "numeric",
                    "business": business, "field": field, "error": message,
                },
            }
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            message = f"berilgen qıymat san emes: {value!r}."
            return {
                "spoken": f"Jaza almadım: {message}",
                "card": {
                    "tool": "remember", "kind": "business_data", "operation": "numeric",
                    "business": business, "field": field, "error": message,
                },
            }
        if value < 0 and field not in _NEGATIVE_ALLOWED_FIELDS:
            label = business_mod.field_label(field)
            message = f"'{label}' maydanı teris (negative) san qabıllamaydı: {value}."
            return {
                "spoken": f"Jaza almadım: {message}",
                "card": {
                    "tool": "remember", "kind": "business_data", "operation": "numeric",
                    "business": business, "field": field, "error": message,
                },
            }
        try:
            business_mod.set_numeric_field(memory_dir, business, field, value, unit)
        except ValueError as e:
            return {
                "spoken": f"Jaza almadım: {e}",
                "card": {
                    "tool": "remember", "kind": "business_data", "operation": "numeric",
                    "business": business, "field": field, "error": str(e),
                },
            }
        label = business_mod.field_label(field)
        unit_shown = unit.strip() if isinstance(unit, str) and unit.strip() else "unknown"
        return {
            "spoken": f'{business} ushın "{label}" maydanına jazdım: {value} {unit_shown}.',
            "card": {
                "tool": "remember", "kind": "business_data", "operation": "numeric",
                "business": business, "field": field, "value": value, "unit": unit_shown,
                "status": "ok",
            },
        }

    fact = (fact or "").strip()
    if not fact:
        return {
            "spoken": "Ne este saqlaw kerekligin túsinbedim, qayta aytıp ber.",
            "card": {"tool": "remember", "file": None, "text": ""},
        }

    if business and field:
        try:
            label = business_mod.field_label(field)
            if append and business_mod.field_type(field) == "list":
                business_mod.append_to_list_field(memory_dir, business, field, fact)
                return {
                    "spoken": f'{business} ushın "{label}" dizimine qostım: "{fact}".',
                    "card": {
                        "tool": "remember",
                        "kind": "business_data",
                        "operation": "append",
                        "business": business,
                        "field": field,
                        "text": fact,
                        "status": "ok",
                    },
                }
            business_mod.set_field(memory_dir, business, field, fact)
            return {
                "spoken": f'{business} ushın "{label}" maydanına jazıp qoydım: "{fact}".',
                "card": {
                    "tool": "remember",
                    "kind": "business_data",
                    "operation": "replace",
                    "business": business,
                    "field": field,
                    "text": fact,
                    "status": "ok",
                },
            }
        except ValueError:
            pass  # belgisiz field-key bolsa, tómendegi business_knowledge jolına ótedi

    if business:
        path = business_mod.add_knowledge_note(memory_dir, business, fact)
        return {
            "spoken": f'{business} haqqında jazıp qoydım: "{fact}".',
            "card": {"tool": "remember", "kind": "business_knowledge", "business": business, "file": path.name, "text": fact},
        }

    path = memory_mod.write(memory_dir, fact)
    return {
        "spoken": f'Jazıp qoydım: "{fact}" — {path.name} faylına.',
        "card": {"tool": "remember", "kind": "personal_memory", "file": path.name, "text": fact},
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
# 6) compute_finance — saqlanǵan numeric sandardan taza arifmetikalıq esap
# ---------------------------------------------------------------------------
#
# BUSINESS DECISION ENGINE — 2-basqısh. Bul tool HESH BIR derekti ÓZI
# IZLEMEYDI hám HESH NÁRSEGE jazbaydı (fayl, business_data, memory — bularǵa
# tiyisi joq, hesh bir API-ge de shaqırmaydı). Ol TEK ózine tool_input
# retinde berilgen numeric qıymatlardan (value+unit) esaplaydı — sandı ÓZI
# OYLAP TAPPAYDI. Haqıyqıy sandardı ALDIN search_brain penen tabıw — bul
# modeldiń jumısı (prompt.md-di qara), compute_finance tek ekinshi qádem.

_MONEY_UNITS = {"UZS", "USD", "KZT"}

_FINANCE_OPERATIONS = {
    "gross_profit": ("revenue", "cost"),
    "margin": ("revenue", "cost"),
    "average_check": ("revenue", "customers"),
    "growth_percent": ("current", "previous"),
    "cash_flow_net": ("revenue", "cost", "fixed_costs"),
}

_NUMERIC_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "value": {"type": "number", "description": "San (numeric qıymat)"},
        "unit": {
            "type": "string",
            "enum": sorted(business_mod.NUMERIC_UNITS),
            "description": "Ólshem birligi",
        },
    },
    "required": ["value", "unit"],
}


def _to_number(raw):
    """raw-di san (float) etip qaytaradı, bolmasa None. Qátelik xabarın bul
    funktsiya QURMAYDI — shaqırıwshı ózi anıq xabar jasaydı."""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        num = float(raw)
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            num = float(text)
        except ValueError:
            return None
    else:
        return None
    if not math.isfinite(num):
        return None
    return num


def _clean_number(num: float):
    """Nátiyjeni eki ondıq orınǵa shekem dóńgelektiredi; pútin bolsa int
    etip qaytaradı (JSON-da '100000000.0' emes, '100000000' kórinsin ushın)."""
    num = round(num, 2)
    return int(num) if float(num).is_integer() else num


def _parse_finance_input(inputs: dict, name: str):
    """`inputs[name]` = {"value":..., "unit":...} kútiledi. Durıs bolsa
    (san, unit, None) qaytaradı, bolmasa (None, None, anıq_qátelik_xabarı)."""
    entry = (inputs or {}).get(name)
    if not isinstance(entry, dict):
        return None, None, f'"{name}" ushın maǵlıwmat berilmegen (kerek forma: {{"value": san, "unit": birlik}}).'

    value = _to_number(entry.get("value"))
    if value is None:
        return None, None, f'"{name}" ushın numeric qıymat durıs emes: {entry.get("value")!r}.'

    unit = entry.get("unit")
    if not isinstance(unit, str) or not unit.strip():
        return None, None, f'"{name}" ushın ólshem birligi (unit) berilmegen.'
    unit = unit.strip()
    if unit not in business_mod.NUMERIC_UNITS:
        return None, None, (
            f'"{name}" ushın belgisiz ólshem birligi: \'{unit}\' — bilinetuǵınlar: '
            f'{", ".join(sorted(business_mod.NUMERIC_UNITS))}.'
        )
    return value, unit, None


def _finance_error(operation: str, message: str) -> dict:
    return {
        "spoken": f"Esaplay almadım: {message}",
        "card": {"tool": "compute_finance", "operation": operation, "error": message},
    }


def _finance_ok(operation: str, used_inputs: dict, result, unit: str, formula: str, spoken: str) -> dict:
    return {
        "spoken": spoken,
        "card": {
            "tool": "compute_finance",
            "operation": operation,
            "inputs": used_inputs,
            "result": {"value": result, "unit": unit},
            "formula": formula,
        },
    }


def compute_finance(operation: str, inputs: dict) -> dict:
    """Saqlanǵan numeric business data-dan (model ALDIN search_brain penen
    tapqan sandardan) taza arifmetikalıq esap shıǵaradı. Fayl oqımaydı/
    jazbaydı, API shaqırmaydı — TEK esaplaw (deterministic)."""
    operation = (operation or "").strip()
    if operation not in _FINANCE_OPERATIONS:
        return _finance_error(
            operation or "(joq)",
            f"belgisiz operatsiya '{operation}' — bilinetuǵınlar: {', '.join(sorted(_FINANCE_OPERATIONS))}.",
        )

    inputs = inputs if isinstance(inputs, dict) else {}
    parsed = {}
    errors = []
    for name in _FINANCE_OPERATIONS[operation]:
        value, unit, err = _parse_finance_input(inputs, name)
        if err:
            errors.append(err)
        else:
            parsed[name] = (value, unit)
    if errors:
        return _finance_error(operation, " ".join(errors))

    used_inputs = {name: {"value": _clean_number(v), "unit": u} for name, (v, u) in parsed.items()}

    if operation == "gross_profit":
        revenue, r_unit = parsed["revenue"]
        cost, c_unit = parsed["cost"]
        if r_unit not in _MONEY_UNITS or c_unit not in _MONEY_UNITS:
            return _finance_error(operation, "revenue hám cost aqsha birliginde boliwı kerek (UZS/USD/KZT).")
        if r_unit != c_unit:
            return _finance_error(operation, f"revenue ({r_unit}) hám cost ({c_unit}) ólshem birlikleri sáykes kelmeydi.")
        raw = revenue - cost
        if not math.isfinite(raw):
            return _finance_error(operation, "esaplaw nátiyjesi jaramsız (NaN/Infinity).")
        result = _clean_number(raw)
        return _finance_ok(
            operation, used_inputs, result, r_unit, "gross_profit = revenue - cost",
            f"Jalpı payda: {result} {r_unit}.",
        )

    if operation == "margin":
        revenue, r_unit = parsed["revenue"]
        cost, c_unit = parsed["cost"]
        if r_unit not in _MONEY_UNITS or c_unit not in _MONEY_UNITS:
            return _finance_error(operation, "revenue hám cost aqsha birliginde boliwı kerek (UZS/USD/KZT).")
        if r_unit != c_unit:
            return _finance_error(operation, f"revenue ({r_unit}) hám cost ({c_unit}) ólshem birlikleri sáykes kelmeydi.")
        if revenue == 0:
            return _finance_error(operation, "revenue 0 — margin esaplanbaydı (nolge bóliw).")
        raw = (revenue - cost) / revenue * 100
        if not math.isfinite(raw):
            return _finance_error(operation, "esaplaw nátiyjesi jaramsız (NaN/Infinity).")
        result = _clean_number(raw)
        return _finance_ok(
            operation, used_inputs, result, "percent",
            "margin_percent = (revenue - cost) / revenue * 100",
            f"Marja: {result} protsent.",
        )

    if operation == "average_check":
        revenue, r_unit = parsed["revenue"]
        customers, cu_unit = parsed["customers"]
        if r_unit not in _MONEY_UNITS:
            return _finance_error(operation, "revenue aqsha birliginde boliwı kerek (UZS/USD/KZT).")
        if cu_unit != "count":
            return _finance_error(operation, f"customers ólshem birligi 'count' boliwı kerek, berilgen: '{cu_unit}'.")
        if customers == 0:
            return _finance_error(operation, "customers 0 — average_check esaplanbaydı (nolge bóliw).")
        raw = revenue / customers
        if not math.isfinite(raw):
            return _finance_error(operation, "esaplaw nátiyjesi jaramsız (NaN/Infinity).")
        result = _clean_number(raw)
        return _finance_ok(
            operation, used_inputs, result, r_unit, "average_check = revenue / customers",
            f"Ortasha chek: {result} {r_unit}.",
        )

    if operation == "growth_percent":
        current, cur_unit = parsed["current"]
        previous, prev_unit = parsed["previous"]
        if cur_unit != prev_unit:
            return _finance_error(operation, f"current ({cur_unit}) hám previous ({prev_unit}) ólshem birlikleri sáykes kelmeydi.")
        if previous == 0:
            return _finance_error(operation, "previous 0 — growth_percent esaplanbaydı (nolge bóliw).")
        raw = (current - previous) / previous * 100
        if not math.isfinite(raw):
            return _finance_error(operation, "esaplaw nátiyjesi jaramsız (NaN/Infinity).")
        result = _clean_number(raw)
        return _finance_ok(
            operation, used_inputs, result, "percent",
            "growth_percent = (current - previous) / previous * 100",
            f"Ósiw: {result} protsent.",
        )

    # operation == "cash_flow_net"
    revenue, r_unit = parsed["revenue"]
    cost, c_unit = parsed["cost"]
    fixed_costs, f_unit = parsed["fixed_costs"]
    if r_unit not in _MONEY_UNITS or c_unit not in _MONEY_UNITS or f_unit not in _MONEY_UNITS:
        return _finance_error(operation, "revenue, cost hám fixed_costs aqsha birliginde boliwı kerek (UZS/USD/KZT).")
    if not (r_unit == c_unit == f_unit):
        return _finance_error(
            operation,
            f"revenue ({r_unit}), cost ({c_unit}) hám fixed_costs ({f_unit}) ólshem birlikleri sáykes kelmeydi.",
        )
    raw = revenue - cost - fixed_costs
    if not math.isfinite(raw):
        return _finance_error(operation, "esaplaw nátiyjesi jaramsız (NaN/Infinity).")
    result = _clean_number(raw)
    return _finance_ok(
        operation, used_inputs, result, r_unit, "cash_flow_net = revenue - cost - fixed_costs",
        f"Aqsha aǵımı: {result} {r_unit}.",
    )


# ---------------------------------------------------------------------------
# 7) diagnose_business — bir biznes ushın verified numeric data + esaplar
# ---------------------------------------------------------------------------
#
# BUSINESS DECISION ENGINE — 2b-basqısh. Bul tool SHESHIM QABILLAMAYDI,
# "eń jaqsı"/"eń jaman" demeydi, sebep te izlemeydi, usınıs bermeydi —
# TEK verified fact + compute_finance() arqalı orınlanǵan esap +
# jetispeytuǵın derekti qaytaradı. Aqırǵı túsindirme/usınıs — model
# ózi, prompt.md-degi "Sheshim dvigateli" arqalı jasaydı.
#
# READ-ONLY: business_data-ǵa hesh nárse jazbaydı (tek load_business() —
# oqıw). ctx["profile"]/ctx["vault"] bul funktsiyaǵa MUDAM berilmeydi
# (qara: run_tool) — iyeniń onboarding juwapları (profile/answers.json)
# hesh qashan ARKAN/ESTELIK/TENAZ-tiń "haqıyqıy financial data"-sı
# retinde qollanılmaydı, tek memory/business_data/<biznes>.json.

_NUMERIC_FIELD_KEYS = sorted(
    k for k in business_mod.known_field_keys() if business_mod.field_type(k) == "numeric"
)

# compute_finance()-tiń rol atları (revenue/cost/customers/fixed_costs) —
# qaysı business_data maydanınan alınatuǵının kórsetedi. "revenue" TEK
# finance.revenue-den alınadı — sales.monthly_sales-ke ESHQASHAN avtomat
# almastırılmaydı (eki bólek túsinik, silliqlap birikpeydi).
_FINANCE_ROLE_TO_FIELD = {
    "revenue": "finance.revenue",
    "cost": "finance.cost",
    "fixed_costs": "finance.fixed_costs",
    "customers": "customers.average_monthly_customers",
}

# "growth_percent"-ten basqa 4 operatsiya — hár qaysısı BIR RET, tuwrı
# field-ler jıynaǵınan (_FINANCE_ROLE_TO_FIELD arqalı) sınaladı.
_DIAGNOSIS_OPERATIONS = ("gross_profit", "margin", "average_check", "cash_flow_net")


def _collect_verified_data(data: dict):
    """Bir biznestiń load_business() nátiyjesinen NUMERIC maydanlardı
    ajıratadı. Tolıq struktura numeric jazba (unit bar, value haqıyqıy
    san) verified_data-ǵa, basqaları (joq, yamasa eski set_field()
    arqalı jazılǵan TEKST-scalar — 'unit' kiliti joq) missing_fields-ke
    túsedi. Hesh bir maǵlıwmat "jaramlı" dep OYLAP TABILMAYDI — tek
    haqıyqıı numeric+unit jazba verified boladı."""
    fields = (data or {}).get("fields") or {}
    verified = {}
    missing = []
    for field_key in _NUMERIC_FIELD_KEYS:
        section, _, field = field_key.partition(".")
        entry = (fields.get(section) or {}).get(field)
        value = entry.get("value") if isinstance(entry, dict) else None
        valid = (
            isinstance(entry, dict)
            and "unit" in entry
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        )
        if not valid:
            missing.append(field_key)
            continue
        item = {"value": value, "unit": entry["unit"], "updated_at": entry.get("updated_at")}
        prev = entry.get("previous")
        if isinstance(prev, dict) and "value" in prev:
            item["previous"] = {
                "value": prev.get("value"),
                "unit": prev.get("unit", "unknown"),
                "updated_at": prev.get("updated_at"),
            }
        verified[field_key] = item
    return verified, missing


def _run_calculations(verified_data: dict):
    """4 bekitilgen operatsiyanı (_FINANCE_ROLE_TO_FIELD arqalı) hám hár
    verified NUMERIC maydan ushın growth_percent-ti compute_finance()
    arqalı sınaydı — formulanı QAYTA JAZBAYDI, tek sonı shaqıradı.
    Qátelik xabarları da tikkeley compute_finance-tiń ÓZINEN alınadı.
    Qaytaradı: (calculations, calculation_gaps)."""
    calculations = {}
    gaps = []

    for operation in _DIAGNOSIS_OPERATIONS:
        inputs = {}
        for role in _FINANCE_OPERATIONS[operation]:
            field_key = _FINANCE_ROLE_TO_FIELD.get(role)
            entry = verified_data.get(field_key) if field_key else None
            if entry:
                inputs[role] = {"value": entry["value"], "unit": entry["unit"]}
        card = compute_finance(operation, inputs).get("card", {})
        if "result" in card:
            calculations[operation] = card["result"]
        else:
            gaps.append({"calculation": operation, "reason": card.get("error", "belgisiz qátelik")})

    growth = {}
    for field_key, entry in verified_data.items():
        inputs = {"current": {"value": entry["value"], "unit": entry["unit"]}}
        prev = entry.get("previous")
        if prev:
            inputs["previous"] = {"value": prev["value"], "unit": prev["unit"]}
        card = compute_finance("growth_percent", inputs).get("card", {})
        if "result" in card:
            growth[field_key] = card["result"]
        else:
            gaps.append({"calculation": "growth_percent", "field": field_key, "reason": card.get("error", "belgisiz qátelik")})

    if growth:
        calculations["growth_percent"] = growth

    return calculations, gaps


def diagnose_business(memory_dir: Path, business: str) -> dict:
    """Bir biznes ushın verified numeric data + compute_finance() arqalı
    orınlanǵan esaplar + jetispeytuǵın derekti jıynaydı. SHESHIM/usınıs
    bermeydi — tek fakt+esap+gap qaytaradı."""
    business = (business or "").strip()
    if not business:
        return {
            "spoken": "Qaysı biznes ushın diagnostika kerekligin túsinbedim.",
            "card": {"tool": "diagnose_business", "business": business, "error": "biznes atı berilmegen"},
        }

    data = business_mod.load_business(memory_dir, business)
    verified_data, missing_fields = _collect_verified_data(data)
    calculations, calculation_gaps = _run_calculations(verified_data)

    if not missing_fields:
        data_quality = "full"
    elif verified_data:
        data_quality = "partial"
    else:
        data_quality = "empty"

    calc_count = (
        len(calculations)
        - (1 if "growth_percent" in calculations else 0)
        + len(calculations.get("growth_percent", {}))
    )
    spoken = (
        f'{business} ushın {len(verified_data)} numeric maydan tabıldı, '
        f'{len(missing_fields)} joq, {calc_count} esap orınlandı.'
    )

    return {
        "spoken": spoken,
        "card": {
            "tool": "diagnose_business",
            "business": business,
            "verified_data": verified_data,
            "missing_fields": missing_fields,
            "calculations": calculations,
            "calculation_gaps": calculation_gaps,
            "data_quality": data_quality,
            "period": "current",
        },
    }


# ---------------------------------------------------------------------------
# 8) instagram_insights — Instagram Business hesabınıń nızıq statistikası
# ---------------------------------------------------------------------------
#
# READ-ONLY: Instagram-nan tek OQIYDI (Graph API GET), hesh nárse jazbaydı/
# postlamaydı (qatań qaǵıyda №1). Baylanıs sazlanbaǵan bolsa yamasa API
# qátelik berse, ANIQ solay aitadı — hesh qashan san oylap tappaydı.


def instagram_insights() -> dict:
    """Instagram Business hesabınıń házirgi statistikaların (jazılıwshı hám
    post sanı) hám aqırǵı postlardıń like/komment sanların Graph API arqalı
    oqıp qaytaradı. Baylanıs sazlanbaǵan bolsa, sonı ANIQ aitadı."""
    if not instagram_mod.is_configured():
        return {
            "spoken": "Instagram baylanısı ele sazlanbaǵan — .env faylında INSTAGRAM_ACCESS_TOKEN joq.",
            "card": {"tool": "instagram_insights", "error": "sazlanbaǵan"},
        }
    try:
        summary = instagram_mod.account_summary()
        media = instagram_mod.recent_media(limit=5)
    except instagram_mod.InstagramError as e:
        return {
            "spoken": f"Instagram-nan maǵlıwmat alıp bolmadım: {e}",
            "card": {"tool": "instagram_insights", "error": str(e)},
        }

    spoken = (
        f"Instagram: @{summary.get('username')} — {summary.get('followers_count')} "
        f"jazılıwshı, {summary.get('media_count')} post. Aqırǵı {len(media)} post tabıldı."
    )
    return {
        "spoken": spoken,
        "card": {"tool": "instagram_insights", "account": summary, "recent_media": media},
    }


# ---------------------------------------------------------------------------
# Anthropic tool-schema-ları hám dispetcher
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "search_brain",
        "description": (
            "Iyeniń jazbalarınan (klientler, ónimler, bahalar, mashqalalar, maqsetler) "
            "naqtı bir faktti izlew. Sorawda belgili biznes atı bolsa, sol biznestiń "
            "struktura maǵlıwmatı (business data) hám erkin jazbaları (business "
            "knowledge) da avtomat qosıladı. Hámishe qaysı fayldan tabılǵanın atap ótiw kerek."
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
            "Bir faktti saqlaw. Tek iye ózi 'esimde saqla' dep sorasa yamasa aytqanı 3 "
            "aydan keyin de kerek boliwı mumkin bolǵanda qollanıladı. Eger fakt belgili "
            "bir biznes haqqında bolsa, 'business' parametrin ber. Eger ol sonıń ústine "
            "struktura maydanǵa da sáykes kelse (aylıq sawda, kirim, maqset h.t.b.), "
            "'field' parametrin de ber. business/field bolmasa, ápiwayı jeke jazba "
            "retinde saqlanadı.\n\n"
            "NUMERIC maydan ushın 'value'+'unit' (BUSINESS DECISION ENGINE): field "
            "NUMERIC-type bolsa (revenue, cost, gross_margin, fixed_costs, cash_flow, "
            "monthly_sales, average_check, average_monthly_customers) HÁM iye AYTQAN "
            "san ANIQ bolsa, 'fact'-tan tısqarı 'value' (san, mısalı 20000000) hám "
            "'unit' (UZS/USD/KZT/percent/count) parametrlerin de qos — usılayınsha "
            "san keleshekte compute_finance ushın da qollanıla aladı. Ólshem birligi "
            "sózden ANIQ bolmasa, 'unit'-ti qaldır (avtomat 'unknown' boladı) — hesh "
            "qashan ózıńnen UZS/USD/KZT tańlama. San ÓZI de anıq aytılmaǵan bolsa "
            "(mısalı 'jaqsı sawda boldı'), 'value'-ni bermey, tek 'fact' jaz. "
            "'value' berilgende bul TEK usı struktura sandı jazadı, ápiwayı tekst "
            "retinde EKINShI RET jazılmaydı.\n\n"
            "ALMASTIRIW vs QOSIW (append): eki qıylı jaǵday bar —\n"
            "1) ESKI QIYMATTI ALMASTIRADI ('ARKAN-nıń aylıq sawdası ENDI 100 mln "
            "som', 'bahası 80-nen 120-ǵa ózgerdi' — bir ólshem jańa qıymatqa ótedi): "
            "'append' bermey qaldır (yamasa false). Bul hámishe scalar maydanlarda "
            "(sawda, kirim, maqset h.t.b.) durı jol.\n"
            "2) BAR DIZIMGE JAŃA ELEMENT QOSADI ('ARKAN-da PRESS stanogi DA bar', "
            "'klientler arasında qurılıs kompaniyaları DA bar' — eskisi qalıp, "
            "ústine biri qosıladı): 'append' true et. Bul TEK type=list "
            "maydanlarda maǵanalı (equipment, main_products, target_customers, "
            "segments, acquisition_channels). Sóz-belgiler ('da', 'tağı', 'bar "
            "eken') kómek beredi, biraq tek olarǵa qarap emes — sáwbet mánisine "
            "qarap sheshiw kerek. Scalar maydanda append=true jiberilse, tool ózi "
            "biykarlap, ápiwayı almastırıw retinde isleydi (qáte bermeydi). "
            "('append' NUMERIC maydanlarda esapqa alınbaydı — olar hesh qashan "
            "dizim emes.)"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fact": {"type": "string", "description": "Saqlanatuǵın fakt, iyeniń óz sózlerinde, sandı ózgertpey"},
                "business": {
                    "type": "string",
                    "description": "Fakt qaysı biznes haqqında (mısalı ARKAN, ESTELIK, TENAZ). Bolmasa qaldır.",
                },
                "field": {
                    "type": "string",
                    "description": "Eger fakt struktura maydanǵa sáykes kelse, sonıń kodı. Sáykes kelmese qaldır.",
                    "enum": business_mod.known_field_keys(),
                },
                "append": {
                    "type": "boolean",
                    "description": (
                        "true — bar dizimge JAŃA element qosıw (tek type=list "
                        "maydanlarda maǵanalı). false yamasa qaldırılsa (standart) — "
                        "eski qıymattı almastırıw. Joğarıdaǵı túsindirmedi qara."
                    ),
                },
                "value": {
                    "type": "number",
                    "description": (
                        "Field NUMERIC-type bolǵanda ǵana qollan — iye ANIQ aytqan san "
                        "(mısalı 20000000). Ólshem belgisiz/ambigúal bolsa, sonda da san "
                        "ózi anıq bolsa qoysań boladı ('unit'-ti qaldır). San ózi anıq "
                        "EMES bolsa (mısalı 'jaqsı boldı'), bul parametrdi ÓZIŃNEN "
                        "OYLAP shıǵarıp bermeyzsen — qaldır, tek 'fact' jaz."
                    ),
                },
                "unit": {
                    "type": "string",
                    "enum": sorted(business_mod.NUMERIC_UNITS),
                    "description": (
                        "'value' menen birge, ólshem birligi. Sózden ANIQ bolmasa "
                        "qaldır (avtomat 'unknown' boladı) — hesh qashan ózıńnen "
                        "shamalap tańlama."
                    ),
                },
            },
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
    {
        "name": "compute_finance",
        "description": (
            "Saqlanǵan numeric biznes sandardan (revenue, cost, customers h.t.b.) TAZA "
            "arifmetikalıq esap shıǵarıw — gross_profit, margin, average_check, "
            "growth_percent, cash_flow_net. Bul tool HESH BIR derekti ÓZI IZLEMEYDI — "
            "kerekli sandardı ALDIN search_brain penen (yamasa sáwbette iye aytqan "
            "naqtı sannan) tabıw SHART, sonnan keyin GHANA usı tool-ge sol NAQ sandı, "
            "ólshem birligi menen birge beriw kerek. Sandı hesh qashan ózıńnen oylap "
            "tappa — kerekli san fayllarda/sáwbette joq bolsa, bul tool-di shaqırma, "
            "'belgisiz' dep ait.\n\n"
            "Operatsiyalar hám kerekli input-lar (inputs ishinde):\n"
            "- gross_profit: revenue, cost → gross_profit = revenue - cost\n"
            "- margin: revenue, cost → margin_percent = (revenue - cost) / revenue * 100\n"
            "- average_check: revenue, customers (customers unit='count') → "
            "average_check = revenue / customers\n"
            "- growth_percent: current, previous (ekewi de BIR TÚRLI birlikte) → "
            "growth_percent = (current - previous) / previous * 100\n"
            "- cash_flow_net: revenue, cost, fixed_costs → "
            "cash_flow_net = revenue - cost - fixed_costs\n\n"
            "Aqsha maydanları (revenue, cost, fixed_costs) bir-birine SÁYKES ólshem "
            "birlikte boliwı kerek (mısalı, ekewi de UZS) — sáykes kelmese yamasa "
            "nolge bóliw kerek bolsa, tool esaplamaydı, ANIQ qátelik qaytaradı."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": sorted(_FINANCE_OPERATIONS),
                    "description": "Qaysı esap túri kerek",
                },
                "inputs": {
                    "type": "object",
                    "description": (
                        "Operatsiyağa kerekli sandar, hár qaysısı {'value':san,'unit':"
                        "birlik} túrinde. Kerekli kilitler operatsiyağa qarap ózgeredi "
                        "(joğarıdaǵı sıpatlamanı qara)."
                    ),
                    "properties": {
                        "revenue": _NUMERIC_INPUT_SCHEMA,
                        "cost": _NUMERIC_INPUT_SCHEMA,
                        "customers": _NUMERIC_INPUT_SCHEMA,
                        "fixed_costs": _NUMERIC_INPUT_SCHEMA,
                        "current": _NUMERIC_INPUT_SCHEMA,
                        "previous": _NUMERIC_INPUT_SCHEMA,
                    },
                },
            },
            "required": ["operation", "inputs"],
        },
    },
    {
        "name": "diagnose_business",
        "description": (
            "Bir biznes ushın SAQLANǴAN numeric business data-nı jıynap, "
            "compute_finance() arqalı bar esaplardı (gross_profit, margin, "
            "average_check, growth_percent, cash_flow_net) AVTOMAT orınlaydı, hám "
            "jetispeytuǵın maǵlıwmattı ANIQ kórsetedi. Bul tool SHESHIM QABILLAMAYDI "
            "— 'eń jaqsı'/'eń jaman' demeydi, sebep izlemeydi, usınıs bermeydi. Tek "
            "úsh nárse qaytaradı: verified_data (naq saqlanǵan sandar), calculations "
            "(orınlanǵan esaplar), missing_fields hám calculation_gaps (ne "
            "jetispeytuǵını ANIQ). Aqırǵı túsindirme/usınıstı SEN ózıń (Sheshim "
            "dvigateli arqalı) jasaysań, usı tool-diń nátiyjesin tiykar etip.\n\n"
            "Bir biznes haqqında keń/quramalı financial analiz kerek bolǵanda "
            "(mısalı 'ARKAN-nıń jaǵdayı qalay', 'payda qanday') usını shaqır — sonda "
            "barlıq numeric derekti hám olardan shıqqan esaplardı BIR shaqırıwda "
            "alasań, hár birewin bólek-bólek compute_finance penen izlewdiń ornına."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "business": {
                    "type": "string",
                    "description": "Diagnostika kerek biznes atı (mısalı ARKAN, ESTELIK, TENAZ)",
                },
            },
            "required": ["business"],
        },
    },
    {
        "name": "instagram_insights",
        "description": (
            "Instagram Business hesabınıń házirgi statistikasın (jazılıwshı sanı, "
            "post sanı) hám aqırǵı 5 posttıń like/komment sanların Meta Graph API "
            "arqalı OQIP beredi. Tek oqıydı — post jazbaydı, jibermeydi, ózgertpeydi. "
            "Instagram baylanısı .env-de sazlanbaǵan bolsa yamasa API qátelik berse, "
            "ANIQ solay aitadı — hesh qashan san oylap tappaydı. Instagram-nıń "
            "jaǵdayı/statistikası soralǵanda (jazılıwshı qansha, aqırǵı post qalay "
            "ótti) usını shaqır."
        ),
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
        return search_brain(v, tool_input.get("query", ""), memory_dir)
    if name == "research_web":
        return research_web(tool_input.get("query", ""), profile)
    if name == "remember":
        return remember(
            memory_dir,
            tool_input.get("fact", ""),
            business=tool_input.get("business", ""),
            field=tool_input.get("field", ""),
            append=bool(tool_input.get("append", False)),
            value=tool_input.get("value"),
            unit=tool_input.get("unit"),
        )
    if name == "plan_day":
        return plan_day(v, profile)
    if name == "brief_me":
        return brief_me(v, memory_dir)
    if name == "compute_finance":
        return compute_finance(tool_input.get("operation", ""), tool_input.get("inputs") or {})
    if name == "diagnose_business":
        # Ataylı TEK memory_dir beriledi — ctx["profile"]/ctx["vault"] usı
        # tool-ge hesh qashan jetpeydi (design-spec №6: profile/answers.json
        # hesh qashan "haqıyqıı financial data" retinde aralaspaydı).
        return diagnose_business(memory_dir, tool_input.get("business", ""))
    if name == "instagram_insights":
        return instagram_insights()

    return {
        "spoken": f"Bunday qural joq: {name}.",
        "card": {"tool": name, "error": "belgisiz tool"},
    }
