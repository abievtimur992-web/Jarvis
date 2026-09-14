"""
list_voices.py — ElevenLabs dawıslarınıń dizimin alıp, hár qaysısınan
qısqa Qaraqalpaqsha úlgi jasaydı — sen qulaq penen tıńlap, birewin
tańlaysań.

Iske túsiriw:  python list_voices.py
Nátiyje: joba túbindegi voices_preview/ papkasına .mp3 fayllar jazıladı.
Fayllardı ashıp tıńla, unaǵanınıń voice_id-in .env faylına usılay jaz:
    ELEVEN_VOICE_ID=<voice_id>
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


_load_dotenv(PROJECT_ROOT / ".env")

import voice as voice_mod  # noqa: E402

SAMPLE_TEXT = "Sálem! Men Jarvis, seniń biznes járdemshiń. Bul meniń dawısım."


def main() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    try:
        voices = voice_mod.list_voices()
    except voice_mod.VoiceError as e:
        print(f"Qátelik: {e}")
        print("ELEVENLABS_API_KEY .env faylında bar ekenin tekser.")
        return

    if not voices:
        print("Hesh qanday dawıs tabılmadı.")
        return

    out_dir = PROJECT_ROOT / "voices_preview"
    out_dir.mkdir(exist_ok=True)

    print(f"{len(voices)} dawıs tabıldı. Hár qaysısınan úlgi jasap atırman...\n")
    for v in voices:
        vid = v["voice_id"]
        name = v["name"] or vid
        safe_name = "".join(c if c.isalnum() else "_" for c in name)
        out_path = out_dir / f"{safe_name}.mp3"
        try:
            audio = voice_mod.speak(SAMPLE_TEXT, vid, bridge=True)
            out_path.write_bytes(audio)
            print(f"  {name}  (voice_id={vid})  ->  {out_path.name}")
        except voice_mod.VoiceError as e:
            print(f"  {name}: qátelik — {e}")

    print(f"\n'{out_dir}' papkasındaǵı .mp3 fayllardı ashıp tıńla (er qaysısın basıp).")
    print("Eń unaǵanın tańlap, onıń voice_id-in .env faylına usılay jaz:")
    print("  ELEVEN_VOICE_ID=<voice_id>")


if __name__ == "__main__":
    main()
