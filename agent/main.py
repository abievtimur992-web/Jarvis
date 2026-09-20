#!/usr/bin/env python3
"""
main.py — Jarvis-tiń júregi: HTTP server + API.

Iske túsiriw:
    python main.py
Soń brauzerde ash: http://localhost:8765

Bul fayl tek Python-diń óz kitapxanasın qollanadı (stdlib) — hesh qanday
sırtqı paket ornatıwdıń keregi joq server tárepinde.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Windows-ta konsol kodirovkasın durıslaymız (á, ǵ, ń h.t.b. durıs shıǵıwı ushın)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

AGENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = AGENT_DIR.parent
UI_DIR = PROJECT_ROOT / "ui"

sys.path.insert(0, str(AGENT_DIR))

import data as data_mod  # noqa: E402
import kaa  # noqa: E402
import tools as tools_mod  # noqa: E402
import vault as vault_mod  # noqa: E402
import voice as voice_mod  # noqa: E402

# ---------------------------------------------------------------------------
# Sazlawlar
# ---------------------------------------------------------------------------

MODEL = "claude-sonnet-5"  # Anthropic model id — birdiń-aq jerde ózgertiledi
FAST_MODEL = "claude-haiku-4-5-20251001"  # dawıs transkriptin durıslaw sıyaqlı jeńil, tez juwap kerek jumıslar ushın
HOST = "127.0.0.1"
PORT = int(os.environ.get("JARVIS_PORT", "8765"))
STT_LANG = os.environ.get("STT_LANG", "kaz")

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
MAX_TOOL_ITERATIONS = 6       # bir sáwbet aylanasında eń kóp tool shaqırıw
MAX_HISTORY_TURNS = 10        # "sońǵı ~10 gezek" — spec talabı
# Sonnet 5 ózi "thinking" (oylaw) ushın da usı shektiń ishinen paydalanadı —
# 1024 júdá az bolıp, oylaw blogı ortasınan kesilip, keyingi gezekte
# Anthropic API-diń "bul blok ózgertilgen" (400) qátelik qaytarıwına alıp
# keletugin edi (kesilgen blok — "originaldan basqa" dep esaplanadı).
MAX_TOKENS = 4096


def load_dotenv(path: Path) -> None:
    """.env faylın kitapxanasız oqıp, os.environ ishine qosadı."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_dotenv(PROJECT_ROOT / ".env")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVEN_VOICE_ID = os.environ.get("ELEVEN_VOICE_ID", "")

# ---------------------------------------------------------------------------
# Vault (jazbalar grafigi) — server baslanǵanda bir ret júklenedi
# ---------------------------------------------------------------------------

_VAULT = None


def get_vault():
    global _VAULT
    if _VAULT is None:
        paths = data_mod.get_vault_paths()
        _VAULT = vault_mod.load_vault(paths)
    return _VAULT


def reload_vault():
    global _VAULT
    _VAULT = None
    return get_vault()


def note_to_json(note, connections: int = 0) -> dict:
    return {
        "id": note.id,
        "title": note.title,
        "type": note.note_type,
        "language": note.language,
        "connections": connections,
        "links": note.links,
    }


def build_graph_json(v: vault_mod.Vault) -> dict:
    hub_counts = v.hub_counts()
    nodes = [note_to_json(n, hub_counts.get(n.id, 0)) for n in v.notes.values()]
    edges = [{"source": s, "target": t} for s, t in v.edges]
    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# Sáwbetlesiw — Anthropic API menen (stdlib urllib arqalı, kitapxanasız)
# ---------------------------------------------------------------------------

_CONVERSATION: list = []  # [{"role": "user"/"assistant", "content": ...}, ...]

NETWORK_RETRIES = 3  # WinError 10054 sıyaqlı ótkinshi tarmaq úzilisleri ushın


def _urlopen_retrying(req: urllib.request.Request, timeout: float):
    """urlopen, biraq ótkinshi tarmaq qátesinde (URLError) 2 ret qayta sınaydı.

    HTTPError (server 4xx/5xx penen juwap berdi) qayta sınalmaydı — bul
    haqıyqıy API qátesi, qayta jiberiw járdem bermeydi."""
    last_err: urllib.error.URLError | None = None
    for attempt in range(NETWORK_RETRIES):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError:
            raise
        except urllib.error.URLError as e:
            last_err = e
            if attempt < NETWORK_RETRIES - 1:
                time.sleep(0.8 * (attempt + 1))
    raise last_err


def _load_system_prompt() -> str:
    parts = []
    prompt_path = AGENT_DIR / "prompt.md"
    if prompt_path.exists():
        parts.append(prompt_path.read_text(encoding="utf-8"))
    claude_md_path = PROJECT_ROOT / "CLAUDE.md"
    if claude_md_path.exists():
        parts.append("\n\n---\n\n" + claude_md_path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _load_profile() -> dict:
    try:
        path = PROJECT_ROOT / "profile" / "answers.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _is_turn_start(message: dict) -> bool:
    """True — bul xabar haqıyqıy jańa gezektiń basy (iyeniń tekst sorawı).
    False — bul tool_use (assistant) yamasa tool_result (user) xabarı,
    yaǵnıy bir gezektiń ORTASI — sonnan kesiw Anthropic API-ge "juwı joq
    tool_result" qátesin beredi."""
    if message.get("role") != "user":
        return False
    content = message.get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        return not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content)
    return True


_THINKING_BLOCK_TYPES = {"thinking", "redacted_thinking"}


def _strip_thinking_blocks(start_index: int) -> None:
    """Sonnet 5 sorlemese de ózi "thinking" bloklarin qosadı — bul bloklar
    bir gezek ishinde (tool orkestraciyası ushın) ANIQ ózgerissiz qaytarılıwı
    kerek, bolmasa Anthropic API "bul blok ózgertilgen" dep 400 qátelik
    qaytaradı. Gezek juwmaqlanıp, _CONVERSATION-ǵa "tarıyx" retinde qalǵanda,
    _trim_history() keyinirek eski xabarlardı óshiriwi múmkin — bul da sol
    talaptı buzıp, KEYINGI gezekte sol qátelikti tuwdıradı. Sonıń ushın gezek
    juwmaqlanǵanda thinking bloklardı alıp taslaymız (bul — Anthropic-tiń
    óziniń qollaǵan qáwipsiz operatsiyası, "óshiriw" hesh qashan "ózgertiw"
    sıyaqlı qátelik bermeydi)."""
    for message in _CONVERSATION[start_index:]:
        if message.get("role") != "assistant":
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        message["content"] = [
            b for b in content if not (isinstance(b, dict) and b.get("type") in _THINKING_BLOCK_TYPES)
        ]


def _trim_history() -> None:
    """Sońǵı ~MAX_HISTORY_TURNS gezekti qaldıradı, biraq kesiw noqatı
    hámishe HAQIYQIY gezek basına tuwrı keliwi kerek — bolmasa qalǵan
    tarıyx tool_use/tool_result jubınıń biri joq halda qaladı, sonda
    Anthropic API 400 qátesin qaytaradı ("tool_use_id ... found in
    tool_result ... no corresponding tool_use")."""
    max_messages = MAX_HISTORY_TURNS * 2
    if len(_CONVERSATION) <= max_messages:
        return
    cut = len(_CONVERSATION) - max_messages
    while cut < len(_CONVERSATION) and not _is_turn_start(_CONVERSATION[cut]):
        cut += 1
    del _CONVERSATION[:cut]


_TOOLS_WITH_CACHE = None


def _tools_for_api() -> list:
    """TOOL_DEFINITIONS, aqırǵı tool-ge cache_control belgisi qosılğan halda.

    system_promptti da, tool sıpatlamaların da hár shaqırıwda qayta-qayta
    tolıq islewdiń ornına, Anthropic bul eki bloktı (tools + system)
    keshi (cache) etip saqlaydı — bul, ásirese bir gezek ishinde tool
    kerek bolğanda bolatuğın ekinshi shaqırıwdı tezletedi."""
    global _TOOLS_WITH_CACHE
    if _TOOLS_WITH_CACHE is None:
        tools = [dict(t) for t in tools_mod.TOOL_DEFINITIONS]
        if tools:
            tools[-1] = {**tools[-1], "cache_control": {"type": "ephemeral"}}
        _TOOLS_WITH_CACHE = tools
    return _TOOLS_WITH_CACHE


def call_anthropic(messages: list, system_prompt: str) -> dict:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY joq")
    body = json.dumps(
        {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "system": [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            "messages": messages,
            "tools": _tools_for_api(),
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=body,
        method="POST",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
    )
    with _urlopen_retrying(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_conversation_turn(user_text: str) -> dict:
    """Bir gezek sáwbet: iye tekstin qabıl etip, aqırǵı juwaptı qaytaradı.

    Gezek ortasında (mısalı, tool ishinde qátelik shıqsa yamasa Anthropic
    HTTPError qaytarsa) qátelik shıqsa, usı gezekte _CONVERSATION-ǵa
    qosılǵannıń HÁMMESI biykarlanadı (rollback). Bolmasa, jarım-jasar
    qalǵan tool_use/tool_result jubı _CONVERSATION-da MÁNGI qalıp,
    KELESI hár bir gezekte de sonı Anthropic-qa jiberip, hámishe sol 400
    qátesin qaytara beredi — server qayta iske túsirilgenshe."""
    turn_start_len = len(_CONVERSATION)
    try:
        return _run_conversation_turn_inner(user_text)
    except Exception:
        del _CONVERSATION[turn_start_len:]
        raise


def _run_conversation_turn_inner(user_text: str) -> dict:
    ctx = {
        "vault": get_vault(),
        "profile": _load_profile(),
        "memory_dir": data_mod.memory_dir(),
    }

    turn_start = len(_CONVERSATION)
    _CONVERSATION.append({"role": "user", "content": user_text})
    system_prompt = _load_system_prompt()
    last_card = None
    tool_log: list = []
    turn_started = time.perf_counter()

    for step in range(MAX_TOOL_ITERATIONS):
        t0 = time.perf_counter()
        response = call_anthropic(list(_CONVERSATION), system_prompt)
        print(f"[waqit] model shaqırıw #{step + 1}: {time.perf_counter() - t0:.2f}s")
        content_blocks = response.get("content", [])
        _CONVERSATION.append({"role": "assistant", "content": content_blocks})

        tool_uses = [b for b in content_blocks if b.get("type") == "tool_use"]
        if not tool_uses:
            text_parts = [b.get("text", "") for b in content_blocks if b.get("type") == "text"]
            final_text = "\n".join(t for t in text_parts if t).strip()
            _strip_thinking_blocks(turn_start)
            _trim_history()
            print(f"[waqit] gezek jámi: {time.perf_counter() - turn_started:.2f}s")
            return {"reply": final_text, "card": last_card, "tool_log": tool_log}

        tool_result_blocks = []
        for tu in tool_uses:
            name = tu.get("name")
            tool_input = tu.get("input", {}) or {}
            t_tool = time.perf_counter()
            result = tools_mod.run_tool(name, tool_input, ctx)
            print(f"[waqit] tool {name}: {time.perf_counter() - t_tool:.2f}s")
            card = result.get("card") or {}
            last_card = card
            tool_log.append({"name": name, "input": tool_input})
            # "spoken" — tek qısqa dawıs juwmaǵı, ekranǵa/modelge tolıq derek
            # emes. Model NAQTI faktlerdi (excerpt, verified_data h.t.b.)
            # kóriw ushın, "card"-tiń tolıq mazmunı da qosıladı — bolmasa
            # model tabılǵan derekti "oqıy" almaydı, tek sanın biledi.
            spoken = result.get("spoken", "")
            card_json = json.dumps(card, ensure_ascii=False)
            tool_result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu.get("id"),
                    "content": f"{spoken}\n\n{card_json}" if spoken else card_json,
                }
            )
        _CONVERSATION.append({"role": "user", "content": tool_result_blocks})

    _strip_thinking_blocks(turn_start)
    _trim_history()
    print(f"[waqit] gezek jámi (shek asıldı): {time.perf_counter() - turn_started:.2f}s")
    return {
        "reply": "Bul soraw ushın júdá kóp qádem kerek boldı — qısqartıp qayta sora.",
        "card": last_card,
        "tool_log": tool_log,
    }


def call_model_simple(instruction: str) -> str:
    """Bir gezeklik, tarixsız model shaqırıwı (dawıs túzetiw ushın)."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY joq")
    body = json.dumps(
        {"model": FAST_MODEL, "max_tokens": 400, "messages": [{"role": "user", "content": instruction}]}
    ).encode("utf-8")
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=body,
        method="POST",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
    )
    with _urlopen_retrying(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
    return "\n".join(t for t in parts if t).strip()


def _build_vocabulary() -> list:
    """Owner atı, brend hám ónim atları — STT-ge kómek beriw ushın sózlik."""
    words: list = []
    profile = _load_profile()
    owner = profile.get("owner") or {}
    if owner.get("name"):
        words.append(owner["name"])
    for b in profile.get("businesses", []):
        if b.get("brand"):
            words.append(b["brand"])
    for note in list(get_vault().notes.values())[:100]:
        words.append(note.title)
    # qaytalanbas etemiz, tártip saqlanadı
    seen = set()
    uniq = []
    for w in words:
        if w and w not in seen:
            seen.add(w)
            uniq.append(w)
    return uniq


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

STATIC_FILES = {"/app.js", "/graph.js", "/styles.css", "/chat.js", "/voice.js"}


class JarvisHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # konsoldı taza saqlaw ushın
        pass

    def _send_json(self, obj, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, base_dir: Path | None = None) -> None:
        if base_dir is not None:
            try:
                path.resolve().relative_to(base_dir.resolve())
            except ValueError:
                self._send_json({"error": "tabılmadı"}, status=404)
                return
        if not path.exists() or not path.is_file():
            self._send_json({"error": "tabılmadı"}, status=404)
            return
        ctype, _ = mimetypes.guess_type(str(path))
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    # ------------------------------------------------------------------
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        qs = parse_qs(parsed.query)

        if route in ("/", ""):
            self._send_file(UI_DIR / "index.html")
        elif route == "/api/graph":
            v = get_vault()
            self._send_json(build_graph_json(v))
        elif route == "/api/note":
            note_id = (qs.get("id") or [""])[0]
            v = get_vault()
            note = v.notes.get(note_id)
            if not note:
                self._send_json({"error": "jazba tabılmadı"}, status=404)
                return
            self._send_json(
                {
                    **note_to_json(note, v.hub_counts().get(note.id, 0)),
                    "text": note.text,
                    "backlinks": note.backlinks,
                    "path": note.rel_path,
                }
            )
        elif route == "/api/search":
            query = (qs.get("q") or [""])[0]
            v = get_vault()
            results = vault_mod.search(v, query, limit=8)
            self._send_json(
                {"results": [{**note_to_json(n), "score": score} for n, score in results]}
            )
        elif route == "/api/status":
            self._send_json(
                {
                    "model_available": bool(ANTHROPIC_API_KEY),
                    "voice_available": bool(ELEVENLABS_API_KEY and ELEVEN_VOICE_ID),
                    "mode": data_mod.mode_label(),
                    "model": MODEL,
                    "stt_lang": STT_LANG,
                }
            )
        elif route == "/api/voices":
            try:
                self._send_json({"voices": voice_mod.list_voices()})
            except voice_mod.VoiceError as e:
                self._send_json({"error": str(e)}, status=503)
        elif route == "/fonts" or route.startswith("/fonts/") or route in STATIC_FILES:
            self._send_file(UI_DIR / route.lstrip("/"), base_dir=UI_DIR)
        else:
            self._send_json({"error": "tabılmadı"}, status=404)

    def do_POST(self) -> None:
        route = urlparse(self.path).path

        if route == "/api/chat":
            payload = self._read_json_body()
            text = (payload.get("text") or "").strip()
            if not text:
                self._send_json({"error": "tekst joq"}, status=400)
                return
            if not ANTHROPIC_API_KEY:
                self._send_json({"model_available": False, "reply": None, "card": None})
                return
            try:
                result = run_conversation_turn(text)
                self._send_json({"model_available": True, **result})
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="replace")[:500]
                self._send_json(
                    {"model_available": True, "error": f"Anthropic API qátesi: {e.code} {detail}"},
                    status=502,
                )
            except Exception as e:  # noqa: BLE001
                self._send_json({"model_available": True, "error": str(e)}, status=502)
        elif route == "/api/reset":
            _CONVERSATION.clear()
            self._send_json({"ok": True})
        elif route == "/api/reload":
            v = reload_vault()
            self._send_json({"ok": True, "notes": len(v.notes)})
        elif route == "/api/listen":
            if not ELEVENLABS_API_KEY:
                self._send_json({"error": "ELEVENLABS_API_KEY joq", "voice_available": False}, status=503)
                return
            length = int(self.headers.get("Content-Length", 0) or 0)
            audio_bytes = self.rfile.read(length) if length else b""
            if not audio_bytes:
                self._send_json({"error": "audio joq"}, status=400)
                return
            content_type = self.headers.get("Content-Type", "audio/webm")
            try:
                raw = voice_mod.listen_raw(audio_bytes, language_code=STT_LANG or None, content_type=content_type)
            except voice_mod.VoiceError as e:
                self._send_json({"error": str(e)}, status=502)
                return
            model_fn = call_model_simple if ANTHROPIC_API_KEY else None
            result = voice_mod.repair_transcript(raw, _build_vocabulary(), model_fn)
            self._send_json(result)
        elif route == "/api/speak":
            if not ELEVENLABS_API_KEY or not ELEVEN_VOICE_ID:
                self._send_json(
                    {"error": "ELEVENLABS_API_KEY yamasa ELEVEN_VOICE_ID .env-de joq"}, status=503
                )
                return
            payload = self._read_json_body()
            text = (payload.get("text") or "").strip()
            if not text:
                self._send_json({"error": "tekst joq"}, status=400)
                return
            bridge = parse_qs(urlparse(self.path).query).get("bridge", ["1"])[0] != "0"
            try:
                audio = voice_mod.speak(text, ELEVEN_VOICE_ID, bridge=bridge)
            except voice_mod.VoiceError as e:
                self._send_json({"error": str(e)}, status=502)
                return
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(len(audio)))
            self.end_headers()
            self.wfile.write(audio)
        else:
            self._send_json({"error": "bul jol tabılmadı: " + route}, status=404)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), JarvisHandler)
    v = get_vault()
    vault_mod.print_index_report(v)
    print(f"\nJarvis iske tústi: http://{HOST}:{PORT}  (rejim: {data_mod.mode_label()})")
    if not ANTHROPIC_API_KEY:
        print("ESKERTIW: ANTHROPIC_API_KEY .env faylında joq — Jarvis sóylese almaydı.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nJarvis toqtatıldı.")


if __name__ == "__main__":
    main()
