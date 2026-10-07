"""
telegram_client.py — Timurdıń óz Telegram akkauntına (MTProto protokolı,
"user" API: api_id/api_hash) jalǵanıw.

Basqa Jarvis modullarınan (voice.py, instagram.py) parqı: bul JALǴIZ
modul SIRTQI PAKET (telethon) talap etedi. Sebebi: Telegram-diń "user"
API-i (jeke sáwbetler, kanallar, gruppalarǵa toliq qol jetimlilik) —
MTProto dep atalatuǵın kúrdeli, shifrlanǵan binar protokol, onı qaytadan
qolmen jazıw qáwipli hám múmkin emes dárejede úlken jumıs. Telethon —
bul protokoldı dógerek sınalǵan, keń qollanılatuǵın kitapxana.

Ornatıw (bir ret, terminalda):
    pip install telethon
    python telegram_login.py

Sazlaw (.env, GIT-GE JAZILMAYDI):
    TELEGRAM_API_ID=...
    TELEGRAM_API_HASH=...
(api_id/api_hash https://my.telegram.org/apps saytınan alınadı.)

telegram_login.py sátli ótkende, `memory/telegram.session` fayli jasaladı
— bul fayl da GIT-GE JAZILMAYDI (.gitignore-de bar), sebebi ol akkauntqa
qayta kiriwsiz kiriw ushın jetkilikli "kilit" bolıp tabıladı.

telethon ornatılmaǵan bolsa yamasa sessiya joq bolsa, is_configured()
False qaytaradı — Jarvis sonıń ushın TOQTAMAYDI, tek bul quraldı
kórsetpeydi (basqa quralları jumıs isteydi)."""

from __future__ import annotations

import os
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent
SESSION_PATH = AGENT_DIR.parent / "memory" / "telegram.session"


class TelegramError(Exception):
    pass


def _telethon_client_class():
    try:
        from telethon.sync import TelegramClient
    except ImportError as e:
        raise TelegramError(
            "telethon kitapxanası ornatılmaǵan — terminalda 'pip install telethon' dep jaz."
        ) from e
    return TelegramClient


def is_configured() -> bool:
    if not (os.environ.get("TELEGRAM_API_ID") and os.environ.get("TELEGRAM_API_HASH")):
        return False
    if not SESSION_PATH.exists():
        return False
    try:
        import telethon  # noqa: F401
    except ImportError:
        return False
    return True


def _client():
    TelegramClient = _telethon_client_class()
    api_id = os.environ.get("TELEGRAM_API_ID", "")
    api_hash = os.environ.get("TELEGRAM_API_HASH", "")
    if not api_id or not api_hash:
        raise TelegramError("TELEGRAM_API_ID/TELEGRAM_API_HASH .env-de joq")
    try:
        api_id_int = int(api_id)
    except ValueError as e:
        raise TelegramError("TELEGRAM_API_ID san bolıwı kerek") from e
    if not SESSION_PATH.exists():
        raise TelegramError(
            "Telegram sessiyası joq — aldın terminalda bir ret 'python telegram_login.py' isle."
        )
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    return TelegramClient(str(SESSION_PATH), api_id_int, api_hash)


def list_dialogs() -> dict:
    """Barlıq chat/kanal/gruppa/jeke sáwbet dizimin (atları hám túrleri)
    qaytaradı (TEK OQIW)."""
    try:
        with _client() as client:
            items = []
            for d in client.get_dialogs():
                if d.is_channel:
                    kind = "kanal"
                elif d.is_group:
                    kind = "gruppa"
                elif d.is_user:
                    kind = "jeke sáwbet"
                else:
                    kind = "basqa"
                items.append({"name": d.name, "kind": kind})
    except TelegramError:
        raise
    except Exception as e:  # noqa: BLE001
        raise TelegramError(str(e)) from e
    return {"dialogs": items}


def recent_messages(chat: str, limit: int = 10) -> dict:
    """Berilgen chat/kanal/gruppadan aqırǵı tekst xabarlardı oqıydı
    (TEK OQIW — hesh nárse jazbaydı/jibermeydi)."""
    try:
        with _client() as client:
            entity = client.get_entity(chat)
            raw_messages = client.get_messages(entity, limit=limit)
            items = []
            for m in raw_messages:
                if not getattr(m, "text", None):
                    continue
                items.append(
                    {
                        "date": m.date.isoformat() if m.date else "",
                        "sender_id": m.sender_id,
                        "text": m.text[:500],
                    }
                )
    except TelegramError:
        raise
    except Exception as e:  # noqa: BLE001 — telethon kóplegen óz qátelik klassın qaytaradı
        raise TelegramError(str(e)) from e
    return {"chat": chat, "messages": items}


def send_message(chat: str, text: str) -> dict:
    """Berilgen chat/kanal/gruppaǵa xabar jiberedi. Bul — JIBERIW
    operaciyası: model bunı TEK iyeniń ANIQ ruqsatınan keyin shaqırıwı
    kerek (prompt.md-dagı qaǵıyda qara, tools.py bul sheklewdi ÓZI
    tekserpeydi — model dárejesinde qadaǵalanadı)."""
    try:
        with _client() as client:
            sent = client.send_message(chat, text)
    except TelegramError:
        raise
    except Exception as e:  # noqa: BLE001
        raise TelegramError(str(e)) from e
    return {"chat": chat, "sent_id": getattr(sent, "id", None)}
