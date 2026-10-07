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
import mcp_client as mcp_mod  # noqa: E402
import tools as tools_mod  # noqa: E402
import vault as vault_mod  # noqa: E402
import voice as voice_mod  # noqa: E402

# ---------------------------------------------------------------------------
# Sazlawlar
# ---------------------------------------------------------------------------

MODEL = os.environ.get("OPENAI_MODEL") or "gpt-6-luna"  # OpenAI model id — birdiń-aq jerde ózgertiledi
HOST = "127.0.0.1"
PORT = int(os.environ.get("JARVIS_PORT", "8765"))
STT_LANG = os.environ.get("STT_LANG", "kaz")

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MAX_TOOL_ITERATIONS = 6       # bir sáwbet aylanasında eń kóp tool shaqırıw
MAX_HISTORY_TURNS = 10        # "sońǵı ~10 gezek" — spec talabı
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

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
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
# Sáwbetlesiw — OpenAI API menen (stdlib urllib arqalı, kitapxanasız)
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
    False — bul assistant (tool shaqırıw) yamasa tool (tool nátiyjesi)
    xabarı, yaǵnıy bir gezektiń ORTASI — sonnan kesiw OpenAI API-ge "juwı
    joq tool nátiyjesi" qátesin beredi."""
    return message.get("role") == "user"


def _trim_history() -> None:
    """Sońǵı ~MAX_HISTORY_TURNS gezekti qaldıradı, biraq kesiw noqatı
    hámishe HAQIYQIY gezek basına tuwrı keliwi kerek — bolmasa qalǵan
    tarıyx tool-shaqırıw/tool-nátiyje jubınıń biri joq halda qaladı, sonda
    OpenAI API qátelik qaytaradı ("tool_call_id ... found in tool message
    ... no corresponding tool call")."""
    max_messages = MAX_HISTORY_TURNS * 2
    if len(_CONVERSATION) <= max_messages:
        return
    cut = len(_CONVERSATION) - max_messages
    while cut < len(_CONVERSATION) and not _is_turn_start(_CONVERSATION[cut]):
        cut += 1
    del _CONVERSATION[:cut]


_TOOLS_FOR_API = None


_BUILTIN_TOOL_NAMES = {t["name"] for t in tools_mod.TOOL_DEFINITIONS}

_INVALID_TOP_LEVEL_SCHEMA_KEYS = {"oneOf", "anyOf", "allOf", "enum", "const"}


def _is_openai_compatible_schema(schema) -> bool:
    """OpenAI-diń function-calling parameters schema-sı EŃ JOQARǴI
    dárejede "type": "object" bolıwı kerek, hám oneOf/anyOf/allOf/enum/
    const sıyaqlı JSON-Schema birikpelerin EŃ JOQARǴI dárejede qabıl
    etpeydi. Sırtqı MCP serverler (Composio h.t.b.) keyde usınday schema
    qaytaradı — aldın-ala súzbesek, OpenAI SOL BIR quraldıń qátesi ushın
    BARLIQ sorawdı biykarlaydı (400), tipti dúz Jarvis quralları da
    islemey qaladı."""
    if not isinstance(schema, dict):
        return False
    if schema.get("type") != "object":
        return False
    if _INVALID_TOP_LEVEL_SCHEMA_KEYS & schema.keys():
        return False
    return True


def _tools_for_api() -> list:
    """TOOL_DEFINITIONS (name/description/input_schema), OpenAI-diń "function
    calling" formatına ótkerilgen halda ({"type": "function", "function":
    {...}}), hám (sazlanǵan bolsa) sırtqı MCP serverdiń (mısalı Composio)
    qurallari da qosılǵan halda. tools.py-diń ózi ózgermeydi — bul tek
    formattı ótkeriw. MCP serverge jetpey qalsa (tarmaq joq, kilit durıs
    emes h.t.b.), sonı ekranǵa jazıp, tek óziniń dúz quralları menen
    dawam etedi — Jarvis sonıń ushın toqtamaydı."""
    global _TOOLS_FOR_API
    if _TOOLS_FOR_API is None:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in tools_mod.TOOL_DEFINITIONS
        ]
        if mcp_mod.is_configured():
            try:
                skipped = []
                for t in mcp_mod.list_tools():
                    params = t.get("inputSchema") or {"type": "object", "properties": {}}
                    if not _is_openai_compatible_schema(params):
                        skipped.append(t["name"])
                        continue
                    tools.append(
                        {
                            "type": "function",
                            "function": {
                                "name": t["name"],
                                "description": t.get("description", ""),
                                "parameters": params,
                            },
                        }
                    )
                if skipped:
                    print(f"[MCP] {len(skipped)} qural OpenAI schema-ǵa sıymaǵanı ushın ótkerildi: {', '.join(skipped)}")
            except mcp_mod.MCPError as e:
                print(f"[MCP] qurallardı alıp bolmadı: {e}")
        _TOOLS_FOR_API = tools
    return _TOOLS_FOR_API


def call_openai(messages: list, system_prompt: str) -> dict:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY joq")
    body = json.dumps(
        {
            "model": MODEL,
            "max_completion_tokens": MAX_TOKENS,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "tools": _tools_for_api(),
            # gpt-6-luna standart "oylaw" (reasoning) rejiminde islep, bul
            # tool (function calling) menen birge islemeydi — "none" etip
            # óshirmesek, Chat Completions API 400 qátelik beredi.
            "reasoning_effort": "none",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        OPENAI_API_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "content-type": "application/json",
        },
    )
    with _urlopen_retrying(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_conversation_turn(user_text: str) -> dict:
    """Bir gezek sáwbet: iye tekstin qabıl etip, aqırǵı juwaptı qaytaradı.

    Gezek ortasında (mısalı, tool ishinde qátelik shıqsa yamasa OpenAI
    HTTPError qaytarsa) qátelik shıqsa, usı gezekte _CONVERSATION-ǵa
    qosılǵannıń HÁMMESI biykarlanadı (rollback). Bolmasa, jarım-jasar
    qalǵan tool-shaqırıw/tool-nátiyje jubı _CONVERSATION-da MÁNGI qalıp,
    KELESI hár bir gezekte de sonı OpenAI-ge jiberip, hámishe qátelik
    qaytara beredi — server qayta iske túsirilgenshe."""
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

    _CONVERSATION.append({"role": "user", "content": user_text})
    system_prompt = _load_system_prompt()
    last_card = None
    tool_log: list = []
    turn_started = time.perf_counter()

    for step in range(MAX_TOOL_ITERATIONS):
        t0 = time.perf_counter()
        response = call_openai(list(_CONVERSATION), system_prompt)
        print(f"[waqit] model shaqırıw #{step + 1}: {time.perf_counter() - t0:.2f}s")
        message = response["choices"][0]["message"]
        _CONVERSATION.append(message)

        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            final_text = (message.get("content") or "").strip()
            _trim_history()
            print(f"[waqit] gezek jámi: {time.perf_counter() - turn_started:.2f}s")
            return {"reply": final_text, "card": last_card, "tool_log": tool_log}

        for tc in tool_calls:
            fn = tc.get("function") or {}
            name = fn.get("name")
            try:
                tool_input = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                tool_input = {}
            t_tool = time.perf_counter()
            if name in _BUILTIN_TOOL_NAMES:
                result = tools_mod.run_tool(name, tool_input, ctx)
            else:
                result = mcp_mod.call_tool(name, tool_input)
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
            _CONVERSATION.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "content": f"{spoken}\n\n{card_json}" if spoken else card_json,
                }
            )

    _trim_history()
    print(f"[waqit] gezek jámi (shek asıldı): {time.perf_counter() - turn_started:.2f}s")
    return {
        "reply": "Bul soraw ushın júdá kóp qádem kerek boldı — qısqartıp qayta sora.",
        "card": last_card,
        "tool_log": tool_log,
    }


def call_model_simple(instruction: str) -> str:
    """Bir gezeklik, tarixsız model shaqırıwı (dawıs túzetiw ushın)."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY joq")
    body = json.dumps(
        {"model": MODEL, "max_completion_tokens": 400, "messages": [{"role": "user", "content": instruction}]}
    ).encode("utf-8")
    req = urllib.request.Request(
        OPENAI_API_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "content-type": "application/json",
        },
    )
    with _urlopen_retrying(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return (data["choices"][0]["message"].get("content") or "").strip()


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
                    "model_available": bool(OPENAI_API_KEY),
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
            if not OPENAI_API_KEY:
                self._send_json({"model_available": False, "reply": None, "card": None})
                return
            try:
                result = run_conversation_turn(text)
                self._send_json({"model_available": True, **result})
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="replace")[:500]
                self._send_json(
                    {"model_available": True, "error": f"OpenAI API qátesi: {e.code} {detail}"},
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
            model_fn = call_model_simple if OPENAI_API_KEY else None
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
    if not OPENAI_API_KEY:
        print("ESKERTIW: OPENAI_API_KEY .env faylında joq — Jarvis sóylese almaydı.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nJarvis toqtatıldı.")


if __name__ == "__main__":
    main()
