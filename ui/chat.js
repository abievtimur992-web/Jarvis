/*
 * chat.js — Jarvis penen tekst arqalı sáwbetlesiw.
 *
 * /api/chat shaqıradı. Model qosılmaǵan bolsa (kilit joq), bunı ASHIQ
 * aytadı hám tek fayllardan izlewge awısadı — hesh qashan izlewdi model
 * juwabı retinde kórsetpeydi ("Routing works without a model" qaǵıydası).
 */

(function () {
  "use strict";

  function cardBodyFromTool(card) {
    if (!card) return "";
    if (card.tool === "search_brain") {
      if (!card.results || !card.results.length) return "Hesh nárse tabılmadı.";
      return card.results
        .map((r) => "• " + r.title + " (" + (r.path || r.type) + ")\n  " + (r.excerpt ? r.excerpt.slice(0, 160) + "…" : ""))
        .join("\n\n");
    }
    if (card.tool === "research_web") {
      return (card.lines || []).join("\n");
    }
    if (card.tool === "remember") {
      return "Fayl: " + card.file + "\nTekst: " + card.text;
    }
    if (card.tool === "plan_day") {
      return (card.items || []).map((it, i) => (i + 1) + ". " + it).join("\n");
    }
    if (card.tool === "brief_me") {
      const notes = (card.recent_notes || []).map((n) => "• " + n.title).join("\n");
      const mem = (card.recent_memory || []).map((m) => "• " + m.file).join("\n");
      return ["Jańa jazbalar:", notes || "(joq)", "", "Yad:", mem || "(joq)"].join("\n");
    }
    return JSON.stringify(card, null, 2);
  }

  async function send(text) {
    const fetchJSON = window.JarvisFetchJSON || ((u) => fetch(u).then((r) => r.json()));
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text }),
      });
      const data = await res.json();

      if (data.model_available === false) {
        const search = await fetchJSON("/api/search?q=" + encodeURIComponent(text));
        const body = search.results.map((r) => "• " + r.title + " (" + r.type + ")").join("\n");
        const spoken = search.results.length
          ? "Model qosılmaǵan, sonlıqtan tek fayllardan izledim: " + search.results.length + " nátiyje."
          : "Model qosılmaǵan, fayllardan da hesh nárse tabılmadı.";
        window.JarvisShowAnswer("MODEL JOQ — TEK IZLEW", spoken, body);
        if (search.results[0] && window.JarvisSelectNote) window.JarvisSelectNote(search.results[0].id);
        if (window.JarvisVoice && window.JarvisVoice.speak) window.JarvisVoice.speak(spoken);
        return;
      }

      if (data.error) {
        window.JarvisShowAnswer("QÁTE", "Jarvis-ta qátelik shıqtı.", data.error);
        return;
      }

      const spoken = data.reply || "...";
      const body = cardBodyFromTool(data.card);
      const badge = data.card ? String(data.card.tool || "sáwbet").toUpperCase() : "SÁWBET";
      window.JarvisShowAnswer(badge, spoken, body);

      if (window.JarvisVoice && window.JarvisVoice.speak) {
        window.JarvisVoice.speak(spoken);
      }
    } catch (e) {
      window.JarvisShowAnswer("QÁTE", "Serverge jete almadım.", String((e && e.message) || e));
    }
  }

  window.JarvisChat = { send: send };
})();
