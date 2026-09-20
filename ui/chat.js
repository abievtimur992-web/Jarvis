/*
 * chat.js — Jarvis penen tekst arqalı sáwbetlesiw.
 *
 * /api/chat shaqıradı. Model qosılmaǵan bolsa (kilit joq), bunı ASHIQ
 * aytadı hám tek fayllardan izlewge awısadı — hesh qashan izlewdi model
 * juwabı retinde kórsetpeydi ("Routing works without a model" qaǵıydası).
 */

(function () {
  "use strict";

  // Business Decision Engine kártalarında (compute_finance, diagnose_business)
  // qaytatın "bólim.maydan" kilitleri hám operatsiya atları — business.py
  // FIELD_SCHEMA-dıń hám tools.py-dıń _FINANCE_OPERATIONS-tıń labellerin
  // qaytaladı (backend-ke API arqalı barmaw ushın, tek kórsetiw ushın).
  var FIELD_LABELS = {
    "finance.revenue": "Kirim",
    "finance.cost": "Shıǵın",
    "finance.gross_margin": "Jalpı marja",
    "finance.fixed_costs": "Turaqlı shıǵınlar",
    "finance.cash_flow": "Aqsha aǵımı",
    "sales.monthly_sales": "Aylıq sawda",
    "sales.average_check": "Ortasha chek",
    "customers.average_monthly_customers": "Aylıq ortasha klient sanı",
  };
  var FINANCE_OP_LABELS = {
    gross_profit: "Jalpı payda",
    margin: "Marja",
    average_check: "Ortasha chek",
    growth_percent: "Ósiw",
    cash_flow_net: "Aqsha aǵımı (net)",
  };
  var DATA_QUALITY_LABELS = { full: "tolıq", partial: "jarım-jartı", empty: "joq" };

  function fieldLabel(key) {
    return FIELD_LABELS[key] || key;
  }

  function formatFinanceValue(value, unit) {
    if (value === undefined || value === null) return "?";
    var num = typeof value === "number" ? value.toLocaleString("ru-RU") : value;
    if (unit === "percent") return num + "%";
    if (!unit || unit === "count" || unit === "unknown") return String(num);
    return num + " " + unit;
  }

  function cardBodyFromTool(card) {
    if (!card) return "";
    if (card.tool === "search_brain") {
      const parts = [];
      if (card.results && card.results.length) {
        parts.push(
          card.results
            .map((r) => "• " + r.title + " (" + (r.path || r.type) + ")\n  " + (r.excerpt ? r.excerpt.slice(0, 160) + "…" : ""))
            .join("\n\n")
        );
      }
      if (card.business) parts.push(card.business);
      return parts.length ? parts.join("\n\n---\n\n") : "Hesh nárse tabılmadı.";
    }
    if (card.tool === "research_web") {
      return (card.lines || []).join("\n");
    }
    if (card.tool === "remember") {
      if (card.kind === "business_data") return "Biznes: " + card.business + "\nMaydan: " + card.field + "\nTekst: " + card.text;
      if (card.kind === "business_knowledge") return "Biznes: " + card.business + "\nTekst: " + card.text;
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
    if (card.tool === "compute_finance") {
      if (card.error) return "Esaplay almadım: " + card.error;
      const opLabel = FINANCE_OP_LABELS[card.operation] || card.operation;
      const result = card.result || {};
      const lines = [opLabel + ": " + formatFinanceValue(result.value, result.unit)];
      if (card.formula) lines.push("Formula: " + card.formula);
      return lines.join("\n");
    }
    if (card.tool === "diagnose_business") {
      if (card.error) return "Diagnostika ótkerilmedi: " + card.error;
      const verified = card.verified_data || {};
      const missing = card.missing_fields || [];
      const calculations = card.calculations || {};
      const gaps = card.calculation_gaps || [];
      const quality = DATA_QUALITY_LABELS[card.data_quality] || card.data_quality || "?";
      const lines = [card.business + " — derek sapası: " + quality + " (bar: " + Object.keys(verified).length + ", joq: " + missing.length + ")"];

      const verifiedKeys = Object.keys(verified);
      if (verifiedKeys.length) {
        lines.push("", "Bar maydanlar:");
        verifiedKeys.forEach((key) => {
          const entry = verified[key];
          lines.push("• " + fieldLabel(key) + ": " + formatFinanceValue(entry.value, entry.unit));
        });
      }

      const calcKeys = Object.keys(calculations).filter((k) => k !== "growth_percent");
      if (calcKeys.length || calculations.growth_percent) {
        lines.push("", "Esaplar:");
        calcKeys.forEach((k) => {
          const res = calculations[k];
          lines.push("• " + (FINANCE_OP_LABELS[k] || k) + ": " + formatFinanceValue(res.value, res.unit));
        });
        if (calculations.growth_percent) {
          Object.keys(calculations.growth_percent).forEach((fk) => {
            const res = calculations.growth_percent[fk];
            lines.push("• " + fieldLabel(fk) + " ósiwi: " + formatFinanceValue(res.value, res.unit));
          });
        }
      }

      if (missing.length) {
        lines.push("", "Jetispeytuǵın maydanlar:", missing.map(fieldLabel).join(", "));
      }
      if (gaps.length) {
        lines.push("", "Esaplanbaǵan operatsiyalar:");
        gaps.forEach((g) => {
          lines.push("• " + (FINANCE_OP_LABELS[g.calculation] || g.calculation) + ": " + g.reason);
        });
      }
      return lines.join("\n");
    }
    if (card.tool === "instagram_insights") {
      if (card.error) return "Instagram: " + card.error;
      const account = card.account || {};
      const media = card.recent_media || [];
      const label = card.competitor ? "Basqa akkaunt" : "Seniń akkauntıń";
      const lines = [
        label + ": @" + (account.username || "?") + " — " + (account.followers_count ?? "?") + " jazılıwshı, " + (account.media_count ?? "?") + " post",
      ];
      if (media.length) {
        lines.push("", "Aqırǵı postlar:");
        media.forEach((m) => {
          const when = m.timestamp ? m.timestamp.slice(0, 10) : "?";
          lines.push("• " + when + " — " + (m.like_count ?? "?") + " layk, " + (m.comments_count ?? "?") + " komment" + (m.caption ? " — " + m.caption : ""));
        });
      }
      return lines.join("\n");
    }
    return JSON.stringify(card, null, 2);
  }

  function spokenSummary(reply) {
    // Uzın, kóp abzatlı juwapta tek birinshi abzat dawısqa aylandırıladı
    // (prompt.md: "Dawıs haqqında" bólimi) — tolıq tekst ekranda qaladı.
    const firstBreak = reply.indexOf("\n\n");
    return firstBreak === -1 ? reply : reply.slice(0, firstBreak).trim();
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

      const reply = data.reply || "...";
      const body = cardBodyFromTool(data.card);
      const badge = data.card ? String(data.card.tool || "sáwbet").toUpperCase() : "SÁWBET";
      window.JarvisShowAnswer(badge, reply, body);

      if (window.JarvisVoice && window.JarvisVoice.speak) {
        window.JarvisVoice.speak(spokenSummary(reply));
      }
    } catch (e) {
      window.JarvisShowAnswer("QÁTE", "Serverge jete almadım.", String((e && e.message) || e));
    }
  }

  window.JarvisChat = { send: send };
})();
