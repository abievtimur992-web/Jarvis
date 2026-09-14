# Jarvis — Timurdıń biznes járdemshisi

Bul seniń úsh biznesiń (ESTELIK, ARKAN, TENAZ) ushın jasalǵan, qaraqalpaqsha
sóylesetuǵın kishi kómekshi. Kompyuteriňde islep, dawıs penen yamasa jazıp
sóylesiwge boladı, jazbalarıńdı grafik túrinde kórsetedi hám 5 quralı bar:
jazbalardan izlew, internetten izlew, este saqlaw, kún jobasın dúziw hám
brifing beriw.

Bul fayl — Jarvis-ti qalay ornatıw, iske túsiriw hám basqarıw haqqında.

---

## 1. Kerekli nárseler

- **Python 3.11 yamasa jańaraq** kompyuteriňde ornatılǵan bolıwı kerek.
  Tekseriw: `cmd`-di ash, `python --version` dep jaz.
  Joq bolsa: python.org/downloads saytınan júkle, ornatqanda
  **"Add python.exe to PATH"** dep jazılǵan qutıshanı belgile.
- Internet baylanısı (izlew, sáwbetlesiw hám dawıs ushın kerek).
- Browser (Chrome, Edge yamasa basqa jańa browser).

Serverdiń ózi hesh qanday sırtqı Python paket talap etpeydi. Sonıń ushın
`pip install` dep atalǵan nárseniń keregi joq.

---

## 2. Jarvis qay jerde jaylasqan

Bul ZIP-ti qanday jerge ashsań, Jarvis sonda jaylasadı. Mısalı, eger
`D:\jarvis` papkasına ashsań, struktura bılay boladı:

```
D:\jarvis\
  agent\       <- Jarvis-tiń "miyi" (Python kodı)
  ui\          <- ekranda kóretuǵın bet (HTML/JS/CSS)
  biznes\      <- seniń NIZIQ jazbalarıń (ESTELIK/ARKAN/TENAZ)
  profile\     <- seniń interyudan jıynalǵan maǵlıwmatıń
  memory\      <- Jarvis "esimde saqla" dep jazǵan fayllar (baslapqıda bos)
  data\        <- demo (oylap tabılǵan) maǵlıwmatlar, sınaw ushın
  .env         <- sazlawlar hám kilitler (bul fayldı hesh kimge kórsetpe)
  CLAUDE.md    <- Jarvis hár sessiyada oqıytuǵın, sen haqqındaǵı qısqasha jazba
  README.md    <- usı fayl
```

**`biznes\` papkası — seniń NIZIQ maǵlıwmatıń.** Onıń ishine qálegeniňdi
jaz: brend jazbaları, klientler, bahalar, mashqalalar, maqsetler, kúndelik
jazbalar. Jarvis onı tek oqıydı, ózi jazbaydı.

---

## 3. Qalay iske túsiriw kerek (Windows)

1. `cmd` (Buyrıqlar qatarı) yamasa PowerShell-di ash.
2. `agent` papkasına ót. Mısalı, eger Jarvis `D:\jarvis` da bolsa:
   ```
   cd D:\jarvis\agent
   ```
3. Usını jaz hám Enter bas:
   ```
   python main.py
   ```
4. Konsolda `Serving on http://localhost:8765` dep jazılǵandı kórgende,
   browserdi ashıp usı adresti jaz: **http://localhost:8765**
5. Jarvis-ti toqtatıw ushın konsolda `Ctrl+C` bas.

Eger `python main.py` "python tabılmadı" desa — Python durıs ornatılmaǵan
yamasa PATH-qa qosılmaǵan (1-bólimdi qara).

**Eskertiw:** Jarvis birinshi ret ashılǵanda **demo rejiminde** ashıladı —
yaǵnıy seniń nızıq maǵlıwmatıń emes, oylap tabılǵan AMANAT/POLAT/BEREKE
degen fiktiv brendlerdi kórsetedi. Bul — qáwipsiz sınaw ushın. Óz
maǵlıwmatıńdı kóriw ushın tómendegi 5-bólimdi oqı.

---

## 4. Kilitlerdi qosıw (dawıs hám sáwbetlesiw ushın)

`.env` faylın (D:\jarvis\.env) Bloknot (Notepad) penen ash. Onda bular bar:

```
ANTHROPIC_API_KEY=
ELEVENLABS_API_KEY=
ELEVEN_VOICE_ID=
STT_LANG=kaz
JARVIS_DEMO=1
JARVIS_PORT=8765
```

- **ANTHROPIC_API_KEY** — sáwbetlesiw hám 5 quraldıń islewi ushın kerek.
  console.anthropic.com saytınan alasań. Bul bos bolsa, Jarvis tek grafik
  hám izlew rejiminde islewin dawam etedi (ekranda "Model joq" degen belgi
  kóriw múmkin — bul buzılıw emes, tek kilit joq degeni).
- **ELEVENLABS_API_KEY** — dawıs (mikrofon hám sóylew) ushın kerek.
  elevenlabs.io saytınan alasań.
- **ELEVEN_VOICE_ID** — qaysı dawıs penen sóylesetuǵınıńdı tańlaw. Kilitti
  qosqannan keyin:
  ```
  cd D:\jarvis\agent
  python list_voices.py
  ```
  Bul dizim shıǵaradı hám hár dawıstıń úlgisin (mp3) `voices_preview\`
  papkasına saqlaydı. Qulaq salıp, jaqqanınıń ID-sin `.env`-ge jaz.

Kilitlerdi jazıp bolǵannan keyin, Jarvis-ti qayta iske túsir (`Ctrl+C`,
sonan soń qayta `python main.py`).

**Bul mániyli:** `.env` fayl `.gitignore`-de bar. Bul jobanı GitHub-qa
jiberseń, `.env` avtomatlı túrde qalıp qaladı, kilitlerin ashıq jibermeydi.
Biraq bul fayldı basqa adamǵa hesh qashan jiberme, onıń ishinde seniń
kilitleriń bar.

---

## 5. Óz maǵlıwmatıńa ótiw (demodan nızıqqa)

`.env` faylında:
```
JARVIS_DEMO=1
```
degendi
```
JARVIS_DEMO=0
```
etip ózgert hám Jarvis-ti qayta iske túsir. Endi Jarvis `biznes\`
papkasındaǵı seniń NIZIQ jazbalarıńdı oqıydı.

Qayta demoǵa qaytıw ushın `JARVIS_DEMO=1` etip qaytadan jaz.

---

## 6. Jańa jazba qosıw

`biznes\` papkasına `.md` (yamasa `.txt`) fayl qos. Jarvis onı avtomatlı
túrde tabadı, server qayta iske túsirilgende. Mısalı, jańa klient ushın:

```
biznes\klientler\jana-klient.md
```

Fayl ishinde basqa jazbaǵa siltew qoyıw ushın qos-kvadrat jaqsha
qollanıladı: `[[ARKAN]]` dep jazsań, bul `arkan.md` jazbasına baylanıs
jasaydı hám grafikte sızıq etip kóriw múmkin boladı.

Server islep atırǵanda jańa fayl qossań, grafikte kóriw ushın betti qayta
júklew kerek (F5).

---

## 7. Dawıstı sazlaw (qaysı til jaqsıraq tanıydı)

Qaraqalpaq tili ushın arnawlı dawıs xızmeti joq, sonıń ushın Jarvis eń
jaqın keletuǵın tildi (qazaqsha yamasa ózbekshe) sınap kóredi. Qaysısı
saǵan jaqsıraq isleytuǵınıńdı tabıw ushın:

```
cd D:\jarvis\agent
python voice_calibrate.py
```

Bul 20 sóylemdi oqıp beriwdi soraydı (browser arqalı jazıladı), sonan soń
hár tildi salıstırıp, eń az qátelik shıǵarǵandı usınıs etedi. Kelisseń, ol
avtomatlı túrde `.env`-ge jazadı.

---

## 8. Profildi jańalaw

`profile\answers.json` — interyudan alınǵan maǵlıwmatıń (biznesleriń,
bahalarıń, klientleriń, maqsetleriń). Bul fayldı Bloknot penen ashıp,
qolmen ózgertiwge boladı (mısalı, jańa baha yamasa jańa maqset qossań).
Jarvis onı hár sáwbette oqıydı.

`CLAUDE.md` — Jarvis-tiń seniń haqqındaǵı qısqasha "esteligi", hár
sessiyada avtomatlı oqıladı. Bunı da qolmen ózgertiwge boladı.

**Ashıq aytayıq:** `CLAUDE.md` hám `agent\prompt.md` fayllar
`.gitignore`-de JOQ. Olar joba qurılısınıń bir bólimi bolǵanı ushın ataylı
qaldırılǵan. Eger bul jobanı óz GitHub akkauntıńa jiberseń, bul eki
fayldaǵı jeke maǵlıwmat (atıń, jaylasqan jeriń, biznes atları) da birge
ketedi. `profile\`, `memory\`, `biznes\` hám `.env` bulardan qáwipsizirek,
olar avtomatlı túrde qalıp qaladı. Eger `CLAUDE.md` hám `prompt.md`-di de
jasırıw kerek bolsa, olardı `.gitignore` faylına qolmen qosıwıńa boladı.

---

## 9. Jarvis ne jaza aladı, ne jazbaydı (qáwipsizlik qaǵıydaları)

Bul qaǵıydalar `agent\prompt.md` faylında tolıq jazılǵan:

1. **Hesh kimge xabar jibermeydi** — email, Telegram, WhatsApp arqalı hesh
   nárse jollamaydı. Bunday múmkinshilik kodta joq.
2. **Tek `memory\` papkasına jaza aladı** — `biznes\` yamasa `profile\`
   papkalarına hesh qashan ózi jazbaydı, tek oqıydı.
3. **Jazǵanın hámishe dawıs penen aytadı** — "esimde saqla" dep sorasań,
   qaysı faylǵa jazǵanın hámishe aytadı, jasırın jazbaydı.
4. **Aqsha jumsamaydı** — tólem, satıp alıw sıyaqlı hesh bir operatsiya
   islemeydi.
5. **San, klient yamasa sáne oylap tappaydı** — bahalar hám sanlar tek
   fayllardan alınadı, fayllarda joq bolsa, "bilmeymen" dep aytadı.
6. **API kilitlerdi hesh qashan kórsetpeydi yamasa aytpaydı** — ekranda da,
   dawısta da kilitler shıqpaydı.

Bulardı óziń tekseriw ushın: `.env`-ge kilitlerdi qos, Jarvis-ti ash,
"meniń ARKAN-nan qansha kirimim bar?" dep sora. Juwaptı
`biznes\brendler\arkan.md` yamasa `profile\answers.json`-nan alǵanın
kóreseń (kartada fayl atı kórsetiledi). Fayllarda joq nárseni sorasań
(mısalı, hesh jerde joq bir protsent sanın sorasań), Jarvis "bilmeymen"
dewi kerek, san oylap tappawı kerek.

---

## 10. Bahalar (xarajat) haqqında

Jarvis ózi aqı almaydı, biraq eki sırtqı xızmet aqılı:

- **Anthropic (model)** — hár sáwbet gezeginde tólenedi (token sanı
  boyınsha). Dawıs penen sóyleskende, transkriptti túzetiw ushın da
  qosımsha bir shaqırıw bar (repair pass), bul da tólem qosadı.
- **ElevenLabs** — mikrofonnan esitiw (minut sanı boyınsha) hám sóylew
  (belgi sanı boyınsha) ushın tólenedi.

Bahalar jıyı ózgeredi, sonıń ushın bul jerde naqtı sanlardı jazbaymız.
anthropic.com/pricing hám elevenlabs.io/pricing saytlarınan házirgi
bahalardı tekser. Az jumsaw ushın demo rejiminde (`JARVIS_DEMO=1`) sınaw,
al nızıq islerde tek kerek waqıtta qollanıw usınıs etiledi.

---

## 11. Eger buzılsa

- **"python tabılmadı"** — Python ornatılmaǵan yamasa PATH-qa qosılmaǵan
  (1-bólimdi qara).
- **Bet ashılmaydı (localhost:8765)** — server islep tur ma, tekser
  (konsolda qátelik bar ma). Basqa programma sol porttı alıp turǵan bolsa,
  `.env`-de `JARVIS_PORT`-ti ózgert.
- **"Model joq" degen belgi** — `.env`-de `ANTHROPIC_API_KEY` bos.
  4-bólimdi qara.
- **Mikrofon islemeydi** — browser mikrofonǵa ruqsat soraydı, "Ruqsat et"
  bas. Sonday-aq `ELEVENLABS_API_KEY` hám `ELEVEN_VOICE_ID` `.env`-de
  bolıwı kerek.
- **Shrift (hárip) kórinisi ózgeshe** — `ui\fonts\` papkasında hárip
  fayllari (Unbounded/Inter/JetBrains Mono) házirshe joq, joba qurılısında
  internet sheklewi sebepli qosılmadı. Bet sonday-aq durıs islewin dawam
  etedi, tek sistemanıń óz shriftin qollanadı. Kerek bolsa, bul úsh
  shriftti Google Fonts saytınan júklep, `.woff2` fayllardı `ui\fonts\`
  papkasına qoysań, dizayn tolıq josparlanǵanday boladı.

---

Soraw tuwılsa, bul fayldı qayta oqı, yamasa `agent\prompt.md` faylınan
Jarvis-tiń tolıq qaǵıydaların kór.
