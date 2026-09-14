"""
voice_calibrate.py — Timurdıń dawısı ushın eń jaqsı STT sazlawın tabadı.

Ne isleydi:
  1. Iyeniń biznesi haqqında 20 Qaraqalpaqsha sóylem oylap tabadı (sanlar,
     som, ónim hám orın atları menen) — tekseriw ushın kórsetedi.
  2. Kishkene brauzer beti ashadı (http://localhost:8766) — sen hár
     sóylemdi dawıstap oqıysań, mikrofon jazıp aladı.
  3. Hár jazbanı úsh túrli sazlaw penen (kaz, uzb, avto) taniydı, model
     penen tuzetedi, hám qátelik dárejesin (CER) esaplaydı.
  4. Eń az qátelik bergen sazlawdı .env faylındaǵı STT_LANG etip usınıs
     etedi.

Iske túsiriw:  python voice_calibrate.py
"""

from __future__ import annotations

import http.server
import json
import os
import random
import socketserver
import sys
import tempfile
import threading
import webbrowser
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

PORT = 8766
N_SENTENCES = 20
CANDIDATE_SETTINGS = [("kaz", "qazaqsha"), ("uzb", "ózbekshe"), (None, "avto-anıqlaw")]


# ---------------------------------------------------------------------------
# 1) 20 sóylem oylap tabıw
# ---------------------------------------------------------------------------


def _load_profile() -> dict:
    path = PROJECT_ROOT / "profile" / "answers.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def generate_sentences(profile: dict, seed: int = 7) -> list:
    rng = random.Random(seed)
    owner = profile.get("owner") or {}
    name = owner.get("name") or "Iye"
    city = owner.get("location") or "Nókis"
    brands = [b.get("brand") for b in profile.get("businesses", []) if b.get("brand")] or ["ARKAN"]

    templates = [
        "Sálem, meniń atım {name}, {city} qalasında jasayman.",
        "{brand} búgin úsh buyırtpa aldı, bahası 1 250 000 som boldı.",
        "Granit estelik tas 550 000 somnan baslanadı.",
        "{brand} sexinde altı jumısshı bar, bári de jaqsı isleydi.",
        "Búgin 20-sentyabrda jańa dúkan ashılady.",
        "Temir ograjdeniye on metrge 3 million som turadı.",
        "{brand} klientleri kóbinese úy salıp atırǵan adamlar.",
        "Bul ay kirim 6 500 000 som boldı, shıǵın onnan kem.",
        "Ózim erteń saǵat toǵızda jumısqa baraman.",
        "{brand} ushın jańa logotip hám reń kerek.",
        "Qarız hám kredit máselesi eń úlken mashqala.",
        "{brand} Instagram betin ashıp, jarnama beriwdi baslaymız.",
        "Bes jumısshı búgin úyge erte ketti.",
        "Ónimniń bahası jigirma procentke asti.",
        "{name} búgin {brand} sexine bardı.",
        "Qapı-warota buyırtpası eki hápte de tayar boladı.",
        "Jaqsı jumıs ushın ráxmet aytaman hámmesine.",
        "{brand} búgin jańa material aldı, elliw mıń somǵa.",
        "Klient telefon etip, bahanı sorady.",
        "Meniń maqsetim úsh ayda qarızdan shıǵıw.",
    ]

    sentences = []
    for i in range(N_SENTENCES):
        t = templates[i % len(templates)]
        brand = brands[i % len(brands)]
        s = t.format(name=name, city=city, brand=brand)
        sentences.append(s)
    rng.shuffle(sentences)
    return sentences[:N_SENTENCES]


def review_sentences(sentences: list) -> list:
    print("\nTómendegi 20 sóylemdi tekser. Durıs bolsa Enter bas.")
    print("Ózgertiw kerek bolsa, nomerin jaz (mısalı: 3), soń jańa tekstin jaz.\n")
    for i, s in enumerate(sentences, 1):
        print(f"  {i:2d}. {s}")

    while True:
        choice = input("\nNomer (ózgertiw ushın) yamasa Enter (dawam etiw): ").strip()
        if not choice:
            break
        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(sentences)):
                print("Bunday nomer joq.")
                continue
        except ValueError:
            print("San jaz.")
            continue
        new_text = input(f"  {idx + 1}. jańa tekst: ").strip()
        if new_text:
            sentences[idx] = new_text
    return sentences


# ---------------------------------------------------------------------------
# 2) Kishkene brauzer beti — jazıp alıw ushın
# ---------------------------------------------------------------------------

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="kaa"><head><meta charset="utf-8">
<title>Jarvis dawıs sazlawı</title>
<style>
body {{ background:#0a0b0d; color:#eee; font-family:sans-serif; display:flex;
  flex-direction:column; align-items:center; padding:40px 20px; }}
#sentence {{ font-size:22px; margin:24px 0; text-align:center; max-width:600px; }}
button {{ font-size:16px; padding:12px 24px; margin:8px; border-radius:8px; border:none;
  cursor:pointer; background:#2b48ad; color:#fff; }}
button.rec {{ background:#d64545; }}
#progress {{ color:#8b909c; margin-top:20px; }}
</style></head>
<body>
  <h2>Jarvis — dawıs sazlawı</h2>
  <div id="sentence">Júklenip atır...</div>
  <div>
    <button id="recBtn">Jazıwdı baslaw</button>
  </div>
  <div id="progress"></div>
<script>
let sentences = [];
let idx = 0;
let recorder, chunks = [], stream;

async function loadSentences() {{
  const res = await fetch('/sentences');
  sentences = await res.json();
  showSentence();
}}

function showSentence() {{
  if (idx >= sentences.length) {{
    document.getElementById('sentence').textContent = 'Tamam! Endi terminalǵa qayt.';
    document.getElementById('recBtn').style.display = 'none';
    return;
  }}
  document.getElementById('sentence').textContent = (idx+1) + '/' + sentences.length + ': ' + sentences[idx];
  document.getElementById('progress').textContent = '';
}}

document.getElementById('recBtn').addEventListener('click', async () => {{
  const btn = document.getElementById('recBtn');
  if (!recorder || recorder.state === 'inactive') {{
    stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
    recorder = new MediaRecorder(stream);
    chunks = [];
    recorder.addEventListener('dataavailable', (e) => chunks.push(e.data));
    recorder.addEventListener('stop', async () => {{
      const blob = new Blob(chunks, {{ type: 'audio/webm' }});
      document.getElementById('progress').textContent = 'Jiberilip atır...';
      await fetch('/upload/' + idx, {{ method: 'POST', body: blob }});
      stream.getTracks().forEach(t => t.stop());
      idx++;
      showSentence();
    }});
    recorder.start();
    btn.textContent = 'Toqtatıw';
    btn.classList.add('rec');
  }} else {{
    recorder.stop();
    btn.textContent = 'Jazıwdı baslaw';
    btn.classList.remove('rec');
  }}
}});

loadSentences();
</script>
</body></html>
"""


def run_calibration_server(sentences: list, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    sentences_json = json.dumps(sentences, ensure_ascii=False).encode("utf-8")
    page_bytes = PAGE_TEMPLATE.encode("utf-8")

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def do_GET(self):
            if self.path == "/" or self.path == "":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(page_bytes)))
                self.end_headers()
                self.wfile.write(page_bytes)
            elif self.path == "/sentences":
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(sentences_json)))
                self.end_headers()
                self.wfile.write(sentences_json)
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            if self.path.startswith("/upload/"):
                idx = self.path.rsplit("/", 1)[-1]
                length = int(self.headers.get("Content-Length", 0) or 0)
                audio = self.rfile.read(length) if length else b""
                (out_dir / f"sample_{idx}.webm").write_bytes(audio)
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(404)
                self.end_headers()

    httpd = socketserver.TCPServer(("127.0.0.1", PORT), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


# ---------------------------------------------------------------------------
# 3) STT eki-úsh sazlaw penen salıstırıw
# ---------------------------------------------------------------------------


def evaluate(sentences: list, out_dir: Path) -> dict:
    scores = {label: [] for _, label in CANDIDATE_SETTINGS}
    for i, ref in enumerate(sentences):
        sample_path = out_dir / f"sample_{i}.webm"
        if not sample_path.exists():
            continue
        audio = sample_path.read_bytes()
        for lang_code, label in CANDIDATE_SETTINGS:
            try:
                raw = voice_mod.listen_raw(audio, language_code=lang_code)
            except voice_mod.VoiceError as e:
                print(f"  [{label}] qátelik: {e}")
                continue
            cer = voice_mod.char_error_rate(ref, raw)
            scores[label].append(cer)
            print(f"  {i+1:2d}. [{label:12s}] CER={cer:.2f}  '{raw[:50]}'")
    return scores


def summarize(scores: dict) -> str:
    print("\n=== Nátiyje (ortasha qátelik dárejesi, CER — az bolsa jaqsı) ===")
    best_label = None
    best_avg = None
    for label, values in scores.items():
        if not values:
            print(f"  {label:12s}: sınaq joq")
            continue
        avg = sum(values) / len(values)
        print(f"  {label:12s}: {avg:.2%}")
        if best_avg is None or avg < best_avg:
            best_avg = avg
            best_label = label
    return best_label or "kaz"


LABEL_TO_CODE = {"qazaqsha": "kaz", "ózbekshe": "uzb", "avto-anıqlaw": "kaz"}


def write_stt_lang(code: str) -> None:
    env_path = PROJECT_ROOT / ".env"
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith("STT_LANG="):
            lines[i] = f"STT_LANG={code}"
            found = True
            break
    if not found:
        lines.append(f"STT_LANG={code}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if not voice_mod.is_configured():
        print("ELEVENLABS_API_KEY .env faylında joq. Aldın onı qos, soń qayta jugir.")
        return

    profile = _load_profile()
    sentences = generate_sentences(profile)
    sentences = review_sentences(sentences)

    out_dir = Path(tempfile.gettempdir()) / "jarvis_voice_calibration"
    httpd = run_calibration_server(sentences, out_dir)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"\nBrauzerde ash: {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    print("Hár sóylemdi dawıstap oqı. Barlıǵın jazıp bolǵanda, mına jerge qayt.")
    input("Barlıq 20 sóylemdi jazıp bolsań, Enter bas... ")

    n_samples = len(list(out_dir.glob("sample_*.webm")))
    print(f"\n{n_samples}/{len(sentences)} jazba tabıldı. Salıstırıp atırman...\n")

    scores = evaluate(sentences, out_dir)
    best_label = summarize(scores)
    best_code = LABEL_TO_CODE.get(best_label, "kaz")

    print(f"\nEń jaqsı nátiyje: {best_label} ({best_code}).")
    answer = input(f".env faylındaǵı STT_LANG={best_code} etip jazayın ba? (awa/joq): ").strip().lower()
    if answer in ("awa", "ha", "y", "yes", ""):
        write_stt_lang(best_code)
        print(f"Jazıldı: STT_LANG={best_code}")
    else:
        print("Ózgertilmedi. Kerek bolsa .env faylın qolmen ózgert.")

    httpd.shutdown()


if __name__ == "__main__":
    main()
