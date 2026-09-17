"""
voice.py — ElevenLabs arqalı dawıs: esitiw (STT) hám sóylew (TTS).

DIQQAT (2026-jıldıń jazıwshısı ushın eskertpe): bul fayldaǵı model atları
(`scribe_v2`, `eleven_v3`) jazılǵan waqıtta https://elevenlabs.io/docs
boyınsha durıs edi. ElevenLabs modellerdi jiyi jańalaydı — eger "model
tabılmadı" degen qátelik shıqsa, sayttan házirgi model atların tekserip,
tómendegi STT_MODEL_ID / TTS_MODEL_ID turaqlılarınan ózgert.

Qaraqalpaq tili ushın tayar dawıs xızmeti joq. Sonıń ushın:
  - Esitiw ushın: Scribe modeline "kaz" (qazaqsha) tilin kórsetemiz —
    qaraqalpaqsha eń jaqın tanılatuǵın til usı (voice_calibrate.py bunı
    qazaqsha/ózbekshe/avto penen salıstırıp, eń jaqsısın tabadı).
  - Sóylew ushın: Eleven v3 model qazaqsha (kaz) qollaydı, qaraqalpaqsha
    joq. Sonıń ushın kaa.to_kazakh_cyrillic() penen háriplerdi "kóprik"
    etemiz — bul durıs audarma emes, tek dıbıstı jaqınlastırıw gipotezası.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid

import kaa

ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"
STT_MODEL_ID = "scribe_v2"
TTS_MODEL_ID = "eleven_v3"
NETWORK_RETRIES = 3  # WinError 10054 sıyaqlı ótkinshi tarmaq úzilisleri ushın


class VoiceError(Exception):
    """Dawıs xızmetinde qátelik (kilit joq, tarmaq joq, API qátesi h.t.b.)."""


def _urlopen_retrying(req: urllib.request.Request, timeout: float):
    """urlopen, biraq ótkinshi tarmaq qátesinde (URLError) 2 ret qayta sınaydı.

    HTTPError qayta sınalmaydı — bul haqıyqıy API qátesi (mısalı, 402/400)."""
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


def _api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not key:
        raise VoiceError("ELEVENLABS_API_KEY .env faylında joq")
    return key


def is_configured() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY"))


# ---------------------------------------------------------------------------
# Dawıslar dizimi (owner qulaq penen tańlaw ushın)
# ---------------------------------------------------------------------------


def list_voices() -> list:
    req = urllib.request.Request(
        f"{ELEVENLABS_API_BASE}/voices",
        headers={"xi-api-key": _api_key()},
    )
    try:
        with _urlopen_retrying(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise VoiceError(f"Dawıslar dizimin alıp bolmadı: {e}") from e
    return [
        {"voice_id": v.get("voice_id"), "name": v.get("name"), "category": v.get("category")}
        for v in data.get("voices", [])
    ]


# ---------------------------------------------------------------------------
# Esitiw (STT)
# ---------------------------------------------------------------------------


def _multipart_body(fields: dict, file_field: str, filename: str, file_bytes: bytes, content_type: str):
    boundary = uuid.uuid4().hex
    parts = []
    for key, value in fields.items():
        if value is None:
            continue
        parts.append(
            (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n").encode(
                "utf-8"
            )
        )
    parts.append(
        (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; "
            f'filename="{filename}"\r\nContent-Type: {content_type}\r\n\r\n'
        ).encode("utf-8")
        + file_bytes
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def listen_raw(audio_bytes: bytes, language_code=None, keyterms=None, content_type: str = "audio/webm") -> str:
    """
    Audio baytlarınan XAM (túzetilmegen) transkriptti aladı.
    language_code=None bolsa — Scribe ózi tildi anıqlaydı (avto rejim).
    """
    fields = {"model_id": STT_MODEL_ID}
    if language_code:
        fields["language_code"] = language_code
    if keyterms:
        fields["keyterms"] = json.dumps(list(keyterms)[:100], ensure_ascii=False)

    body, ctype = _multipart_body(fields, "file", "audio.webm", audio_bytes, content_type)
    req = urllib.request.Request(
        f"{ELEVENLABS_API_BASE}/speech-to-text",
        data=body,
        method="POST",
        headers={"xi-api-key": _api_key(), "Content-Type": ctype},
    )
    try:
        with _urlopen_retrying(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:200]
        raise VoiceError(f"Esitiw qátesi: {e.code} {detail}") from e
    except urllib.error.URLError as e:
        raise VoiceError(f"Internetke jete almadım: {e}") from e
    return data.get("text", "") or ""


def repair_transcript(raw_text: str, vocabulary, call_model_fn) -> dict:
    """
    Xam transkriptti durıs Qaraqalpaqsha jazıwǵa túzetedi.

    call_model_fn — main.py-dan beriletuǵın, bir tekstti model arqalı
    ótkerip, juwaptı tekst etip qaytaratuǵın function. None bolsa (model
    joq), túzetiw ótkerilmeydi.

    Qaytaradı: {"raw": ..., "repaired": ..., "model_used": bool}
    """
    raw_text = raw_text or ""
    if not raw_text.strip() or call_model_fn is None:
        return {"raw": raw_text, "repaired": raw_text, "model_used": False}

    vocab_hint = ", ".join(list(vocabulary)[:60]) if vocabulary else "(joq)"
    instruction = (
        "Tómendegi xam sóylew transkriptin TEK imlasın (spellingin) durıs "
        "Qaraqalpaqsha latın jazıwǵa (á ó ú ı ń ǵ háripleri menen) túzet. "
        "Mazmunın ózgertpe, sorawǵa juwap berme, izahat qospa — tek "
        "túzetilgen tekstti qaytar. Bul sózler ushırasıwı mumkin: "
        f"{vocab_hint}\n\nXam tekst: {raw_text}"
    )
    try:
        repaired = (call_model_fn(instruction) or "").strip()
        return {"raw": raw_text, "repaired": repaired or raw_text, "model_used": True}
    except Exception:
        return {"raw": raw_text, "repaired": raw_text, "model_used": False}


# ---------------------------------------------------------------------------
# Sóylew (TTS)
# ---------------------------------------------------------------------------


def speak(text: str, voice_id: str, bridge: bool = True, language_code: str | None = None) -> bytes:
    """
    Tekstti dawısqa aylandıradı, mp3 baytların qaytaradı.

    bridge=True (standart) — kaa.to_kazakh_cyrillic() arqalı qazaq dıbısına
    jaqınlastıradı. bridge=False — sanaqlaw (A/B) ushın, sózlerdi
    ózgertpey jiberedi (?bridge=0 debug tumbler UI-de).

    language_code=None (standart) — TTS_MODEL_ID (eleven_v3) "kaz" kodın
    qabıl etpeydi (validation_error), sonıń ushın tildi kórsetpeymiz, model
    Kirill jazıwınan (bridge nátiyjesi) ózi jaqınlastıradı.
    """
    if not voice_id:
        raise VoiceError("ELEVEN_VOICE_ID .env faylında joq — list_voices.py penen tańla")

    speakable = kaa.to_speakable(text)
    payload_text = kaa.to_kazakh_cyrillic(speakable) if bridge else speakable

    payload = {"text": payload_text, "model_id": TTS_MODEL_ID}
    if language_code:
        payload["language_code"] = language_code
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{ELEVENLABS_API_BASE}/text-to-speech/{voice_id}",
        data=body,
        method="POST",
        headers={
            "xi-api-key": _api_key(),
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    try:
        with _urlopen_retrying(req, timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:200]
        raise VoiceError(f"Sóylew qátesi: {e.code} {detail}") from e
    except urllib.error.URLError as e:
        raise VoiceError(f"Internetke jete almadım: {e}") from e


# ---------------------------------------------------------------------------
# Character Error Rate (voice_calibrate.py ushın)
# ---------------------------------------------------------------------------


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[-1]


def char_error_rate(reference: str, hypothesis: str) -> float:
    """0.0 = mudamı durıs, 1.0 = túgel basqasha. kaa.casefold penen salıstırıladı."""
    ref = kaa.casefold(reference) or ""
    hyp = kaa.casefold(hypothesis) or ""
    if not ref:
        return 0.0 if not hyp else 1.0
    return _levenshtein(ref, hyp) / len(ref)
