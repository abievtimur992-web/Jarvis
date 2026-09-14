"""
data.py — HÁMMEsinen JALǴIZ, naq maǵlıwmatqa tiyisli fayl.

Basqa hesh bir fayl (main.py, tools.py, vault.py...) ózi qaysı papkanı
oqıw kerekligin sheshpeydi — bári usı jerden soraydı. Sonıń ushın
demo/haqıyqıy rejimin almastırıw TEK usı jerde boladı — basqa fayllarǵa
tiymeydi.

JARVIS_DEMO ózgeriwshisi:
  "1" yamasa qoyılmaǵan (standart) -> data/demo/ — oylap tabılǵan
      fixture-lar, klasste kórsetiw hám jazıp alıw ushın qáwipsiz.
  "0" -> Timurdıń óz jazba papkası (profil ishindegi vault_path, standart
      bolsa biznes/).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_AGENT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _AGENT_DIR.parent


def is_demo_mode() -> bool:
    """JARVIS_DEMO ózgeriwshisin oqıydı. Standart — demo (qáwipsiz)."""
    return os.environ.get("JARVIS_DEMO", "1") != "0"


def mode_label() -> str:
    return "DEMO" if is_demo_mode() else "HAQIYQIY"


def get_vault_paths() -> list:
    """Jarvis oqıytuǵın papka jolların qaytaradı (tizim, birneshe boliwi múmkin)."""
    if is_demo_mode():
        demo_dir = _PROJECT_ROOT / "data" / "demo"
        return [str(demo_dir)]

    vault_path = _PROJECT_ROOT / "biznes"
    try:
        answers_path = _PROJECT_ROOT / "profile" / "answers.json"
        if answers_path.exists():
            with open(answers_path, "r", encoding="utf-8") as f:
                answers = json.load(f)
            configured = (answers.get("data_location") or {}).get("vault_path")
            if configured:
                candidate = Path(configured)
                if not candidate.is_absolute():
                    candidate = _PROJECT_ROOT / candidate
                vault_path = candidate
    except Exception:
        # Profil oqılmasa da Jarvis joǵalıp qalmawı kerek — standartqa qaytadı
        pass
    return [str(vault_path)]


def memory_dir() -> Path:
    """memory/ papkasın qaytaradı, joq bolsa jasaydı. Jazıw TEK usı papkaǵa."""
    d = _PROJECT_ROOT / "memory"
    d.mkdir(parents=True, exist_ok=True)
    return d


def profile_paths():
    """CLAUDE.md hám answers.json jolların qaytaradı."""
    return (
        _PROJECT_ROOT / "CLAUDE.md",
        _PROJECT_ROOT / "profile" / "answers.json",
    )
