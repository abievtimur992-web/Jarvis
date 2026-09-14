"""
generate_demo.py — demo ushın oylap tabılǵan (fake) biznes jazbaların jasaydı.

Bul script HESH QASHAN Timurdıń naqtı atın, brend atların yamasa naqtı
klient/san maǵlıwmatların qollanbaydı — bári oylap tabılǵan, biraq
answers.json-daǵı biznes túri, qala hám baha aralıǵına uqsas etip qurılǵan.

Iske túsiriw: python generate_demo.py
Nátiyje: ../data/demo/ papkasına jazıladı (fixed seed — hár gez birdey
nátiyje shıǵadı).
"""

from __future__ import annotations

import random
from pathlib import Path

SEED = 42
OUT_DIR = Path(__file__).resolve().parent / "demo"

# Oylap tabılǵan brend atları — Timurdıń naqtı brend atları EMES
BRAND_ESTELIK = "AMANAT"   # estelik tas + temir qorshaw (ESTELIK-ke uqsas biznes túri)
BRAND_ARKAN = "POLAT"      # swarka sexi (ARKAN-ǵa uqsas biznes túri)
BRAND_TENAZ = "BEREKE"     # qapı dúkanı (TENAZ-ǵa uqsas biznes túri)

CITY = "Shımbay rayonı"  # interview-de aytılǵan qala saqlanadı (jasırın emes)

CLIENT_FIRST_NAMES = [
    "Bekzat", "Aygúl", "Nurlan", "Perizat", "Dawlet", "Gúlnara",
    "Sardar", "Aynur", "Jaqsıbay", "Marjan", "Ilyas", "Botagóz",
]


def rand_price(low: int, high: int, step: int = 50_000, rng: random.Random = None) -> int:
    rng = rng or random
    n = rng.randint(low // step, high // step)
    return n * step


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    rng = random.Random(SEED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- Brendler ------------------------------------------------------
    write(
        OUT_DIR / "brendler" / "amanat.md",
        f"""# {BRAND_ESTELIK}

Estelik tas hám temir qorshawlar islep shıǵarıw hám satıw (demo maǵlıwmat).

- Jaylasqan jeri: {CITY}
- Baha: [[onimler-hem-bahalar]] betin qara
- Klientler: [[amanat-klient-1]], [[amanat-klient-2]]
- Logotip reńi: qara fon, altın-sarı

Baylanıslı: [[mashqalalar]], [[maqsetler]]
""",
    )
    write(
        OUT_DIR / "brendler" / "polat.md",
        f"""# {BRAND_ARKAN}

Swarka sexi — temir qayta islew, ograjdeniye, temir qapı-warota islep
shıǵarıw hám kóshe swarshılarına xızmet kórsetiw (demo maǵlıwmat).

- Jaylasqan jeri: {CITY}
- Baha: [[onimler-hem-bahalar]] betin qara
- Klientler: [[polat-klient-1]], [[polat-klient-2]]
- Logotip reńi: kók + portokal

Baylanıslı: [[mashqalalar]], [[maqsetler]]
""",
    )
    write(
        OUT_DIR / "brendler" / "bereke.md",
        f"""# {BRAND_TENAZ}

Ishki hám sırtqı qapılar satatuǵın dúkan (demo maǵlıwmat).

- Jaylasqan jeri: {CITY}
- Baha: [[onimler-hem-bahalar]] betin qara
- Klientler: [[bereke-klient-1]]

Baylanıslı: [[mashqalalar]], [[maqsetler]]
""",
    )

    # --- Ónimler hám bahalar --------------------------------------------
    granit = rand_price(500_000, 600_000, rng=rng)
    ograjdeniye_low = rand_price(1_500_000, 2_500_000, rng=rng)
    ograjdeniye_high = rand_price(5_000_000, 6_000_000, rng=rng)
    qapı_low = rand_price(1_000_000, 2_000_000, rng=rng)
    qapı_high = rand_price(4_000_000, 5_000_000, rng=rng)

    write(
        OUT_DIR / "onimler-hem-bahalar.md",
        f"""# Ónimler hám bahalar (demo)

## [[{BRAND_ESTELIK}]]
- Granit estelik tas — {granit:,} som
- Temir ograjdeniye (10 metr) — {ograjdeniye_low:,} – {ograjdeniye_high:,} som

## [[{BRAND_ARKAN}]]
- Ograjdeniye/reshotka, temir qapı-warota — ónim boyınsha baha ózgeredi

## [[{BRAND_TENAZ}]]
- Ishki hám sırtqı qapılar — {qapı_low:,} – {qapı_high:,} som

Baylanıslı: [[mashqalalar]], [[maqsetler]]
""".replace(",", " "),
    )

    # --- Mashqalalar -----------------------------------------------------
    write(
        OUT_DIR / "mashqalalar.md",
        f"""# Mashqalalar (demo)

## Finans
- Pul jetispewshiligi — aldıńǵı jıllardaǵı zıyannan qalǵan kreditler.
- Kirim: [[{BRAND_ESTELIK}]]-tan ayına shama menen 4 million som,
  [[{BRAND_ARKAN}]]-tan 6.5 million som.

## Marketing
- [[{BRAND_ARKAN}]], [[{BRAND_ESTELIK}]] hám [[{BRAND_TENAZ}]] ushın SMM/target
  jarnama joq. Instagram islep baslanbaǵan.

Baylanıslı: [[onimler-hem-bahalar]], [[maqsetler]]
""",
    )

    # --- Maqsetler ---------------------------------------------------------
    write(
        OUT_DIR / "maqsetler.md",
        f"""# Maqsetler (keyingi 3 ay, demo)

1. [[{BRAND_ESTELIK}]], [[{BRAND_ARKAN}]] hám [[{BRAND_TENAZ}]] ushın
   rawajlanıw strategiyasın islep shıǵıw.
2. Finanstı basqarıw hám qarızlardan shıǵıw.
3. SMM/target jarnama jolǵa qoyıw.
4. AI qurallardı úyreniw hám óz agentin jaratıw.

Baylanıslı: [[mashqalalar]]
""",
    )

    # --- Klientler (oylap tabılǵan atlar) ---------------------------------
    names = rng.sample(CLIENT_FIRST_NAMES, 5)
    write(
        OUT_DIR / "klientler" / "amanat-klient-1.md",
        f"""# {names[0]}-aga (demo klient)

- Brend: [[{BRAND_ESTELIK}]]
- Ne satıp aldı: granit estelik tas
- Eskertpe: klient jaqınınan ayrılǵan, jılı sóylesiw kerek.
""",
    )
    write(
        OUT_DIR / "klientler" / "amanat-klient-2.md",
        f"""# {names[1]} (demo klient)

- Brend: [[{BRAND_ESTELIK}]]
- Ne satıp aldı: temir ograjdeniye, 10 metr
""",
    )
    write(
        OUT_DIR / "klientler" / "polat-klient-1.md",
        f"""# "{names[2]} qurılıs" firması (demo klient, B2B)

- Brend: [[{BRAND_ARKAN}]]
- Buyırtpa: 20 metr ograjdeniye
""",
    )
    write(
        OUT_DIR / "klientler" / "polat-klient-2.md",
        f"""# {names[3]} (demo klient)

- Brend: [[{BRAND_ARKAN}]]
- Buyırtpa: úy ushın temir qapı-warota, úy salıp atır
""",
    )
    write(
        OUT_DIR / "klientler" / "bereke-klient-1.md",
        f"""# {names[4]} (demo klient)

- Brend: [[{BRAND_TENAZ}]]
- Buyırtpa: 3 sırtqı, 6 ishki qapı, jańa úy ushın
""",
    )

    # --- Kúndelik jazbalar ---------------------------------------------
    write(
        OUT_DIR / "kundelik" / "2026-09-08.md",
        f"""# 8-sentyabr, 2026 (demo kúndelik)

- [[{BRAND_ARKAN}]]: {names[2]} qurılıs firmasınan jańa buyırtpa keldi.
- [[{BRAND_ESTELIK}]]: bir klient bahanı surap edi, hám ele juwap berilmedi.

Baylanıslı: [[mashqalalar]]
""",
    )
    write(
        OUT_DIR / "kundelik" / "2026-09-10.md",
        f"""# 10-sentyabr, 2026 (demo kúndelik)

- [[{BRAND_TENAZ}]] dúkanı ushın jańa qapı úlgileri keldi.
- Bygin material alıwǵa 1 200 000 som jumsaldı.

Baylanıslı: [[mashqalalar]]
""",
    )

    # --- Kóp tilli mısallar (til anıqlawdı tekseriw ushın) -----------------
    write(
        OUT_DIR / "qosımsha" / "kirill-jazba.md",
        f"""# Кирилше жазба (демо)

Бул жазба Қарақалпақ кирил алфавитинде жазылған, тексериў ушын: ғ, қ, ң, ө,
ү, ў, ҳ ҳәриплери бар. [[{BRAND_ARKAN}]] темир қапылар сатады.
""",
    )
    write(
        OUT_DIR / "qosımsha" / "orissha-xabar.md",
        """# Русское сообщение (демо)

Это тестовое сообщение на русском языке для проверки определения языка.
Клиент спрашивает про доставку.
""",
    )
    write(
        OUT_DIR / "qosımsha" / "ozbekcha-xabar.md",
        """# O'zbekcha xabar (demo)

Bu o'zbek tilida test xabari, til aniqlashni tekshirish uchun. Mijoz
eshiklar narxini so'radi.
""",
    )

    print(f"Demo maǵlıwmatlar jasaldı: {OUT_DIR}")


if __name__ == "__main__":
    main()
