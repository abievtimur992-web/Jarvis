"""
instagram.py — Instagram Business hesabınıń nızıq maǵlıwmatın (Meta Graph
API arqalı) oqıw: profil statistikaları hám aqırǵı jazbalar.

Tek OQIW (GET) — bul modul hesh qashan post jazbaydı, jibermeydi, xabar
qaldırmaydı, hesh nárseni ózgertpeydi (qatań qaǵıyda №1, prompt.md-da).

Barlıq san (followers_count, like_count h.t.b.) TIKKELEY Graph API-den
keledi — hesh qashan ózinen shıǵarılmaydı; API qátelik bergende ANIQ
qátelik qaytadı, "boljaw" islenbeydi.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
NETWORK_RETRIES = 3  # ótkinshi tarmaq úzilisleri ushın


class InstagramError(Exception):
    """Instagram Graph API-de qátelik (kilit joq, ID joq, API qátesi h.t.b.)."""


def _urlopen_retrying(req: urllib.request.Request, timeout: float):
    """urlopen, biraq ótkinshi tarmaq qátesinde (URLError) qayta sınaydı.

    HTTPError qayta sınalmaydı — bul haqıyqıy API qátesi (mısalı, 400/401)."""
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


def _access_token() -> str:
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    if not token:
        raise InstagramError("INSTAGRAM_ACCESS_TOKEN .env faylında joq")
    return token


def _business_account_id() -> str:
    account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
    if not account_id:
        raise InstagramError("INSTAGRAM_BUSINESS_ACCOUNT_ID .env faylında joq")
    return account_id


def is_configured() -> bool:
    return bool(os.environ.get("INSTAGRAM_ACCESS_TOKEN")) and bool(
        os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    )


def _get(path: str, fields: dict) -> dict:
    params = dict(fields or {})
    params["access_token"] = _access_token()
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{GRAPH_API_BASE}/{path}?{query}")
    try:
        with _urlopen_retrying(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise InstagramError(f"Instagram API qátesi: {e.code} {detail}") from e
    except urllib.error.URLError as e:
        raise InstagramError(f"Internetke jete almadım: {e}") from e


def account_summary() -> dict:
    """Profildiń házirgi statistikaları: username, jazılıwshı hám post sanı."""
    account_id = _business_account_id()
    data = _get(account_id, {"fields": "username,name,followers_count,media_count"})
    return {
        "username": data.get("username"),
        "name": data.get("name"),
        "followers_count": data.get("followers_count"),
        "media_count": data.get("media_count"),
    }


def recent_media(limit: int = 5) -> list:
    """Aqırǵı jazbalar: like/komment sanı, waqtı, qısqa caption."""
    account_id = _business_account_id()
    data = _get(
        f"{account_id}/media",
        {
            "fields": "id,caption,like_count,comments_count,timestamp,media_type,permalink",
            "limit": limit,
        },
    )
    items = []
    for item in data.get("data", []):
        caption = item.get("caption") or ""
        items.append(
            {
                "id": item.get("id"),
                "caption": caption[:80],
                "like_count": item.get("like_count"),
                "comments_count": item.get("comments_count"),
                "timestamp": item.get("timestamp"),
                "media_type": item.get("media_type"),
                "permalink": item.get("permalink"),
            }
        )
    return items


def business_discovery(username: str) -> dict:
    """Basqa (kompetitor) Instagram Business/Creator hesabınıń ashıq
    (public) statistikasın "Business Discovery" arqalı oqıydı. Tek public
    Business/Creator hesaplar ushın isleydi — jeke (personal) profil
    ushın Graph API ANIQ qátelik qaytaradı, bul funktsiya sonı oylap
    tappaydı, TIKKELEY sol qátelikti kóteredi."""
    account_id = _business_account_id()
    fields = (
        f"business_discovery.username({username})"
        "{username,name,followers_count,media_count,biography,"
        "media.limit(5){id,caption,like_count,comments_count,timestamp,media_type,permalink}}"
    )
    data = _get(account_id, {"fields": fields})
    discovery = data.get("business_discovery")
    if not discovery:
        raise InstagramError(
            f"'{username}' ushın maǵlıwmat tabılmadı — bul akkaunt Business/Creator "
            "túrinde emes yamasa atı qáte boliwı mumkin."
        )

    media_items = []
    for item in (discovery.get("media") or {}).get("data", []):
        caption = item.get("caption") or ""
        media_items.append(
            {
                "id": item.get("id"),
                "caption": caption[:80],
                "like_count": item.get("like_count"),
                "comments_count": item.get("comments_count"),
                "timestamp": item.get("timestamp"),
                "media_type": item.get("media_type"),
                "permalink": item.get("permalink"),
            }
        )
    return {
        "username": discovery.get("username"),
        "name": discovery.get("name"),
        "followers_count": discovery.get("followers_count"),
        "media_count": discovery.get("media_count"),
        "biography": discovery.get("biography"),
        "recent_media": media_items,
    }
