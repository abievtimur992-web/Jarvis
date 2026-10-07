"""
mcp_client.py — sırtqı MCP (Model Context Protocol) serverge jalǵanıw ushın
kishi klient (mısalı, Composio: https://connect.composio.dev/mcp). voice.py
hám instagram.py-diń úlgisi menen bir túrli: tek stdlib (urllib, json),
network qátelerinde qayta urınıw, hesh qanday sırtqı paket kerek emes.

MCP — JSON-RPC 2.0 protokolı, "Streamable HTTP" transport arqalı: POST
sorawlar, juwap "application/json" yamasa "text/event-stream" (SSE) túrinde
qaytadı. Bul klient eki túrdi de qollap-quwatlaydı, biraq hámishe TEK
AQIRǴI juwaptı kútedi (bir soraw → bir juwap) — haqıyqıy ósip barıwshı
(streaming) oqıwdıń keregi joq, sebebi Jarvis-tiń tool-shaqırıw aylanası bir
ret juwap alıp, sonı modelge qaytaradı.

Sazlaw (.env, GIT-GE JAZILMAYDI):
    MCP_SERVER_URL=https://connect.composio.dev/mcp
    MCP_API_KEY=...
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

MCP_PROTOCOL_VERSION = "2025-06-18"
NETWORK_RETRIES = 3


class MCPError(Exception):
    pass


def _urlopen_retrying(req: urllib.request.Request, timeout: float):
    """urlopen, biraq ótkinshi tarmaq qátesinde (URLError) qayta sınaydı.
    HTTPError (server juwap berdi, biraq qátelik penen) qayta sınalmaydı."""
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


def is_configured() -> bool:
    return bool(os.environ.get("MCP_SERVER_URL") and os.environ.get("MCP_API_KEY"))


def _server_url() -> str:
    url = os.environ.get("MCP_SERVER_URL", "")
    if not url:
        raise MCPError("MCP_SERVER_URL .env-de joq")
    return url


def _api_key() -> str:
    key = os.environ.get("MCP_API_KEY", "")
    if not key:
        raise MCPError("MCP_API_KEY .env-de joq")
    return key


def parse_response_body(content_type: str, raw: str) -> dict:
    """Juwap denesin oqıydı — "application/json" yamasa "text/event-stream"
    (SSE) eki túrin de qollap-quwatlap, AQIRǴI JSON-RPC xabardı qaytaradı.

    SSE aǵımında "data: ..." dep baslanatuǵın jollar bir xabardıń bólegi,
    bos qatar xabardı juwmaqlaydı — eń soyǵı tolıq oqılǵan xabar alınadı."""
    if "text/event-stream" in content_type:
        message = None
        for event in raw.split("\n\n"):
            data_lines = [
                line[len("data:"):].strip() for line in event.splitlines() if line.startswith("data:")
            ]
            if not data_lines:
                continue
            try:
                message = json.loads("\n".join(data_lines))
            except json.JSONDecodeError:
                continue
        if message is None:
            raise MCPError("MCP serverden juwap SSE-de tabılmadı")
        return message
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise MCPError(f"MCP serverden juwap JSON emes: {e}") from e


_session_id: str | None = None
_next_id = 1
_initialized = False
_TOOLS_CACHE: list | None = None


def _rpc_call(method: str, params: dict, *, expect_response: bool = True) -> dict:
    global _session_id, _next_id
    body = {"jsonrpc": "2.0", "method": method, "params": params}
    if expect_response:
        body["id"] = _next_id
        _next_id += 1
    headers = {
        "content-type": "application/json",
        "accept": "application/json, text/event-stream",
        "x-consumer-api-key": _api_key(),
        "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
    }
    if _session_id:
        headers["Mcp-Session-Id"] = _session_id
    req = urllib.request.Request(
        _server_url(),
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers=headers,
    )
    try:
        with _urlopen_retrying(req, timeout=30) as resp:
            session_header = resp.headers.get("Mcp-Session-Id")
            if session_header:
                _session_id = session_header
            if not expect_response:
                return {}
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise MCPError(f"MCP HTTP qátesi {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise MCPError(f"MCP serverge jetpedi: {e}") from e

    if not expect_response:
        return {}
    message = parse_response_body(content_type, raw)
    if "error" in message:
        err = message["error"]
        raise MCPError(f"MCP qátesi: {err.get('message', err) if isinstance(err, dict) else err}")
    return message.get("result", {})


def _ensure_initialized() -> None:
    global _initialized, _session_id, _next_id
    if _initialized:
        return
    _session_id = None
    _next_id = 1
    _rpc_call(
        "initialize",
        {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "jarvis", "version": "1.0"},
        },
    )
    _rpc_call("notifications/initialized", {}, expect_response=False)
    _initialized = True


def list_tools() -> list:
    """MCP serverdegi barlıq quraldı qaytaradı:
    [{"name": ..., "description": ..., "inputSchema": {...}}, ...].
    Nátiyje server bir ret soralǵannan soń keshte (cache) saqlanadı."""
    global _TOOLS_CACHE
    if _TOOLS_CACHE is not None:
        return _TOOLS_CACHE
    _ensure_initialized()
    result = _rpc_call("tools/list", {})
    _TOOLS_CACHE = result.get("tools", [])
    return _TOOLS_CACHE


def call_tool(name: str, arguments: dict) -> dict:
    """Bir MCP quraldı shaqıradı, basqa Jarvis quralları menen bir túrli
    {"spoken": str, "card": dict} formatında qaytaradı — hesh qashan
    qátelik kóterpeydi (tool-shaqırıw aylanası toqtamawı kerek)."""
    try:
        _ensure_initialized()
        result = _rpc_call("tools/call", {"name": name, "arguments": arguments or {}})
    except MCPError as e:
        return {
            "spoken": f"'{name}' quralında qátelik: {e}",
            "card": {"tool": name, "source": "mcp", "error": str(e)},
        }
    content = result.get("content", [])
    text_parts = [
        c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
    ]
    text = "\n".join(t for t in text_parts if t)
    is_error = bool(result.get("isError"))
    return {
        "spoken": text[:200] if text else ("Qátelik shıqtı." if is_error else "Orınlandı."),
        "card": {"tool": name, "source": "mcp", "result": text, "is_error": is_error},
    }
