/*
 * app.js — bettiń "tereńlik joq" bólimi: maǵlıwmattı serverden alıp,
 * panellerdi toltıradı hám grafik penen baylanıstıradı.
 *
 * Dawıs (voice.js) hám sáwbetlesiw (chat.js) bólimleri keyingi basqıshlarda
 * qosıladı; olar joq bolsa da bul fayl ózi islewi kerek (izlew arqalı).
 */

(function () {
  "use strict";

  const canvas = document.getElementById("graph-canvas");
  const graph = new window.JarvisGraph(canvas);

  const state = {
    types: new Map(),
    status: null,
  };

  const EXAMPLE_PROMPTS = [
    "ARKAN-nıń klientleri kimler?",
    "ESTELIK-tiń bahaların aytıp ber",
    "Búgingi kún jobasın dúz",
    "TENAZ haqqında bir zat esimde qaldır",
    "Aqshamız qaydan kiredi, qayda ketedi?",
  ];
  let exampleIdx = 0;

  function setExample() {
    const el = document.getElementById("ask-example");
    if (!el) return;
    el.textContent = "Mısalı: " + EXAMPLE_PROMPTS[exampleIdx % EXAMPLE_PROMPTS.length];
    exampleIdx++;
  }
  setExample();
  setInterval(setExample, 6000);

  async function fetchJSON(url, opts) {
    const res = await fetch(url, opts);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || "HTTP " + res.status);
    }
    return res.json();
  }
  window.JarvisFetchJSON = fetchJSON; // chat.js/voice.js ushın da paydalanıladı

  function renderNote(note) {
    document.getElementById("inspector-empty").style.display = "none";
    const box = document.getElementById("inspector-note");
    box.classList.add("visible");
    document.getElementById("note-title").textContent = note.title;
    document.getElementById("note-meta").textContent =
      note.type + " · " + note.language + " · " + note.connections + " baylanıs";
    document.getElementById("note-body").textContent = note.text || "";
  }

  const TYPE_COLORS = {
    brendler: "#4d6cf0",
    klientler: "#e8722c",
    kundelik: "#3fb27f",
    jazba: "#c9cdd6",
    qosımsha: "#a78bfa",
  };

  function buildFilters(nodes) {
    const counts = new Map();
    nodes.forEach((n) => counts.set(n.type, (counts.get(n.type) || 0) + 1));
    const container = document.getElementById("filter-items");
    container.innerHTML = "";
    state.types = new Map();
    for (const [type, count] of counts.entries()) {
      state.types.set(type, true);
      const row = document.createElement("div");
      row.className = "filter-row";
      const swatch = document.createElement("span");
      swatch.className = "swatch";
      swatch.style.background = TYPE_COLORS[type] || "#8b909c";
      const label = document.createElement("span");
      label.className = "label";
      label.appendChild(swatch);
      label.appendChild(document.createTextNode(type));
      const countEl = document.createElement("span");
      countEl.className = "count";
      countEl.textContent = String(count);
      row.appendChild(label);
      row.appendChild(countEl);
      row.addEventListener("click", () => {
        const active = state.types.get(type);
        state.types.set(type, !active);
        row.classList.toggle("disabled", active);
        applyFilters();
      });
      container.appendChild(row);
    }
  }

  function applyFilters() {
    const allActive = [...state.types.values()].every(Boolean);
    if (allActive) {
      graph.setFilter(null);
    } else {
      const activeSet = new Set([...state.types.entries()].filter(([, v]) => v).map(([k]) => k));
      graph.setFilter(activeSet);
    }
  }

  function buildHubs(nodes) {
    const top = [...nodes].sort((a, b) => (b.connections || 0) - (a.connections || 0)).slice(0, 10);
    const container = document.getElementById("hubs-items");
    container.innerHTML = "";
    top.forEach((n) => {
      const row = document.createElement("div");
      row.className = "hub-item";
      const title = document.createElement("span");
      title.textContent = n.title;
      const count = document.createElement("span");
      count.className = "count";
      count.textContent = String(n.connections || 0);
      row.appendChild(title);
      row.appendChild(count);
      row.addEventListener("click", () => selectNote(n.id));
      container.appendChild(row);
    });
  }

  async function selectNote(id) {
    try {
      const note = await fetchJSON("/api/note?id=" + encodeURIComponent(id));
      renderNote(note);
      graph.focusNodeById(id);
    } catch (e) {
      console.error("Jazba júklenbedi:", e);
    }
  }
  window.JarvisSelectNote = selectNote;

  graph.onClick = (node) => { if (node) selectNote(node.id); };

  async function loadGraph() {
    const data = await fetchJSON("/api/graph");
    graph.setData(data);
    buildFilters(data.nodes);
    buildHubs(data.nodes);
  }
  window.JarvisReloadGraph = loadGraph;

  // --- Status badge ("Model joq" h.t.b.) ---
  async function checkStatus() {
    const badge = document.getElementById("status-badge");
    try {
      const status = await fetchJSON("/api/status");
      state.status = status;
      if (!status.model_available) {
        badge.textContent = "Model joq — .env-ge ANTHROPIC_API_KEY qos";
        badge.classList.add("visible");
      } else {
        badge.classList.remove("visible");
      }
    } catch (e) {
      badge.textContent = "Server penen baylanıs joq";
      badge.classList.add("visible");
    }
  }
  checkStatus();
  setInterval(checkStatus, 15000);

  // --- Ask bar ---
  const input = document.getElementById("ask-input");
  const sendBtn = document.getElementById("btn-send");

  function showAnswerCard(badgeText, spoken, body) {
    const card = document.getElementById("answer-card");
    card.classList.add("visible");
    document.getElementById("answer-badge").textContent = badgeText;
    document.getElementById("answer-spoken").textContent = spoken;
    document.getElementById("answer-body").textContent = body || "";
  }
  window.JarvisShowAnswer = showAnswerCard;

  async function sendQuery() {
    const q = input.value.trim();
    if (!q) return;
    input.value = "";
    if (window.JarvisChat && window.JarvisChat.send) {
      await window.JarvisChat.send(q);
      return;
    }
    // Sáwbetlesiw ele qosılmaǵan bolsa — tek izlew isleydi
    try {
      const data = await fetchJSON("/api/search?q=" + encodeURIComponent(q));
      const body = data.results.map((r) => "• " + r.title + " (" + r.type + ")").join("\n");
      showAnswerCard(
        "IZLEW",
        data.results.length
          ? '"' + q + '" boyınsha ' + data.results.length + " jazba tabıldı."
          : '"' + q + '" boyınsha hesh nárse tabılmadı.',
        body
      );
      if (data.results[0]) selectNote(data.results[0].id);
    } catch (e) {
      showAnswerCard("QÁTE", "Izlewde qátelik shıqtı.", String(e.message || e));
    }
  }

  sendBtn.addEventListener("click", sendQuery);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendQuery();
  });

  // --- Túymeler (mikrofon/dawıs keyingi basqıshta tolıq isleydi) ---
  document.getElementById("btn-mic").addEventListener("click", () => {
    if (window.JarvisVoice && window.JarvisVoice.toggleMic) {
      window.JarvisVoice.toggleMic();
    } else {
      showAnswerCard("DAWIS", "Dawıs bólimi ele qosılmaǵan.", "Bul 4-basqıshta qosıladı.");
    }
  });
  document.getElementById("btn-mute").addEventListener("click", (e) => {
    if (window.JarvisVoice && window.JarvisVoice.toggleMute) {
      window.JarvisVoice.toggleMute(e.currentTarget);
    } else {
      e.currentTarget.classList.toggle("active");
    }
  });
  document.getElementById("btn-brief").addEventListener("click", () => {
    if (window.JarvisChat && window.JarvisChat.send) window.JarvisChat.send("brifing ber");
    else showAnswerCard("SÁWBETLESIW", "Sáwbetlesiw ele qosılmaǵan.", "Bul 3-basqıshta qosıladı.");
  });
  document.getElementById("btn-plan").addEventListener("click", () => {
    if (window.JarvisChat && window.JarvisChat.send) window.JarvisChat.send("búgingi kún jobasın dúz");
    else showAnswerCard("SÁWBETLESIW", "Sáwbetlesiw ele qosılmaǵan.", "Bul 3-basqıshta qosıladı.");
  });
  document.getElementById("btn-remember").addEventListener("click", () => {
    const text = prompt("Neni este saqlaw kerek?");
    if (!text) return;
    if (window.JarvisChat && window.JarvisChat.send) window.JarvisChat.send("esimde saqla: " + text);
    else showAnswerCard("SÁWBETLESIW", "Sáwbetlesiw ele qosılmaǵan.", "Bul 3-basqıshta qosıladı.");
  });

  loadGraph().catch((e) => console.error("Grafik júklenbedi:", e));
})();
