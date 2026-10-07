#!/usr/bin/env python3
"""
telegram_login.py — Telegram akkauntına BIR RET kiriw ushın skript.

Ne isleydi:
  1. .env faylınan TELEGRAM_API_ID/TELEGRAM_API_HASH-ti oqıydı
     (https://my.telegram.org/apps saytınan alınadı).
  2. Telefon nomerindi soraydı, Telegram jibergen kodtı soraydı (hám,
     eki basqıshlı tekseriw (2FA) qosılǵan bolsa, parolındı da).
  3. Sátli ótse, `memory/telegram.session` faylın jasaydı — bul faylda
     Jarvis-tiń qaytadan telefon/kod sorawsız kiriwi ushın jetkilikli
     maǵlıwmat bar, sonıń ushın ol da GIT-GE JAZILMAYDI (.gitignore-de).

Iske túsiriw (bir ret jetkilikli):
    pip install telethon
    python telegram_login.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = AGENT_DIR.parent
sys.path.insert(0, str(AGENT_DIR))


def _load_dotenv(path: Path) -> None:
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


def main() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    _load_dotenv(PROJECT_ROOT / ".env")

    api_id = os.environ.get("TELEGRAM_API_ID", "")
    api_hash = os.environ.get("TELEGRAM_API_HASH", "")
    if not api_id or not api_hash:
        print("QÁTE: .env faylında TELEGRAM_API_ID hám/yamasa TELEGRAM_API_HASH joq.")
        print("Birinshi https://my.telegram.org/apps saytınan alıp, .env-ge qos.")
        sys.exit(1)

    try:
        api_id_int = int(api_id)
    except ValueError:
        print("QÁTE: TELEGRAM_API_ID san bolıwı kerek.")
        sys.exit(1)

    try:
        from telethon.sync import TelegramClient
    except ImportError:
        print("QÁTE: telethon kitapxanası ornatılmaǵan.")
        print("Terminalda usını jaz: pip install telethon")
        sys.exit(1)

    session_path = PROJECT_ROOT / "memory" / "telegram.session"
    session_path.parent.mkdir(parents=True, exist_ok=True)

    print("Telegram akkauntına kiriw baslanadı.")
    print("Telefon nomerindi xalıqaralıq formatta jaz (mısalı: +998901234567).")
    with TelegramClient(str(session_path), api_id_int, api_hash) as client:
        client.start()
        me = client.get_me()
        name = getattr(me, "first_name", "") or getattr(me, "username", "") or "?"
        print(f"\nSátli kirdiń: {name}")
        print(f"Sessiya saqlandı: {session_path}")
        print("Endi Jarvis-ti (python main.py) iske túsirseń, Telegram qurallari islewi kerek.")


if __name__ == "__main__":
    main()
