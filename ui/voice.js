/*
 * voice.js — dawıs kirisi (MediaRecorder) hám shıǵısı (Audio elementi).
 *
 * Barlıq dawıs isi serverde boladı: /api/listen (esitiw), /api/speak
 * (sóylew). Brauzerdiń óz Web Speech API-i qollanılmaydı — kilitler
 * brauzerge shıqpaydı.
 *
 * Gezek alıw: mikrofon túymesin bir basasań, sonnan keyin jay sóyleysen.
 * SILENCE_MS mudamı úndemewden keyin gezek avtomat juwmaqlanadı.
 */

(function () {
  "use strict";

  const SILENCE_MS = 900; // sóylep bolǵannan keyingi usınsha úndemewden soń gezek juwmaqlanadı
  const SILENCE_THRESHOLD = 0.02; // dawıs deńgeyi bunnan tómen — "úndemew"
  const LEVEL_POLL_MS = 80; // audio-deńgey tekseriw aralıǵı
  const SPEECH_TIMEOUT_MS = 12000; // sóylew baslanbasa, mikrofon usınsha waqıttan keyin ózi jabıladı

  const state = {
    mic: null,
    recorder: null,
    audioCtx: null,
    analyser: null,
    levelInterval: null,
    silenceStartedAt: null,
    listening: false,
    muted: false,
    currentAudio: null,
    chunks: [],
    hasSpoken: false,
    listenStartedAt: null,
  };

  function setReactor(mode, label) {
    const ring = document.getElementById("reactor-ring");
    const labelEl = document.getElementById("reactor-label");
    if (!ring || !labelEl) return;
    ring.classList.remove("listening", "thinking", "speaking");
    if (mode) ring.classList.add(mode);
    labelEl.textContent = label;
  }

  function setCaption(raw, repaired) {
    const box = document.getElementById("caption");
    const rawEl = document.getElementById("caption-raw");
    const repEl = document.getElementById("caption-repaired");
    if (!box) return;
    if (!raw && !repaired) {
      box.classList.remove("visible");
      return;
    }
    box.classList.add("visible");
    rawEl.textContent = raw || "";
    repEl.textContent = repaired || "";
  }

  function stopSpeaking() {
    if (state.currentAudio) {
      state.currentAudio.pause();
      state.currentAudio.currentTime = 0;
      state.currentAudio = null;
    }
  }

  async function speak(text) {
    if (state.muted) return;
    stopSpeaking();
    setReactor("speaking", "Sóylep atırman");
    try {
      const res = await fetch("/api/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const reason = body.error || ("HTTP " + res.status);
        console.warn("Dawıs joq:", reason);
        // speak() hámishe chat.js-tiń JarvisShowAnswer(...) nátiyjege JAZǴANINAN
        // KEYIN shaqırıladı — sonı "DAWIS JOQ" penen almastırıw eki jazba juwaptı
        // jasıradı. Sonıń ushın tek reactor-labelda kórsetemiz, kártanı tiymeymiz.
        setReactor(null, "Dawıs islemedi (juwap ekranda)");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      state.currentAudio = audio;
      audio.addEventListener("ended", () => {
        if (state.currentAudio === audio) state.currentAudio = null;
        setReactor(null, "Tayar");
      });
      audio.play().catch((e) => {
        console.error("audio.play qátesi:", e);
        setReactor(null, "Dawıs islemedi (juwap ekranda)");
      });
    } catch (e) {
      console.error("speak qátesi:", e);
      setReactor(null, "Dawıs islemedi (juwap ekranda)");
    }
  }

  function stopMicLoop() {
    if (state.levelInterval) {
      clearInterval(state.levelInterval);
      state.levelInterval = null;
    }
    if (state.audioCtx) {
      state.audioCtx.close().catch(() => {});
      state.audioCtx = null;
    }
  }

  function stopMic() {
    stopMicLoop();
    if (state.recorder && state.recorder.state !== "inactive") {
      state.recorder.stop();
    }
    if (state.mic) {
      state.mic.getTracks().forEach((t) => t.stop());
      state.mic = null;
    }
    state.listening = false;
    const btn = document.getElementById("btn-mic");
    if (btn) btn.classList.remove("active");
  }

  async function sendAudio(blob) {
    setReactor("thinking", "Oylap atırman");
    try {
      const res = await fetch("/api/listen", {
        method: "POST",
        headers: { "Content-Type": blob.type || "audio/webm" },
        body: blob,
      });
      const data = await res.json();
      if (data.error) {
        setCaption("", "");
        if (window.JarvisShowAnswer) window.JarvisShowAnswer("DAWIS JOQ", "Esitiw islemedi.", data.error);
        setReactor(null, "Tayar");
        return;
      }
      if (!data.model_used) {
        setCaption(data.raw, "Model joq — transkript dúzetilmedi");
      } else {
        setCaption(data.raw, data.repaired);
      }
      const finalText = data.repaired || data.raw || "";
      if (finalText && window.JarvisChat) {
        await window.JarvisChat.send(finalText);
      } else {
        if (window.JarvisShowAnswer)
          window.JarvisShowAnswer(
            "DAWIS JOQ",
            "Dawısıńızdı tolıq túsinbedim, sorawdı qayta aytıp beriń.",
            ""
          );
        setReactor(null, "Tayar");
      }
    } catch (e) {
      if (window.JarvisShowAnswer) window.JarvisShowAnswer("QÁTE", "Esitiwde qátelik shıqtı.", String((e && e.message) || e));
      setReactor(null, "Tayar");
    }
  }

  async function startMic() {
    if (state.listening) return;
    stopSpeaking(); // mikrofon qosılǵanda, Jarvis ózi sóylep atırǵan bolsa toqtaydı ("mic goes deaf while it speaks")

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      if (window.JarvisShowAnswer)
        window.JarvisShowAnswer("MIKROFON JOQ", "Mikrofonǵa ruqsat berilmedi.", String((e && e.message) || e));
      return;
    }
    state.mic = stream;
    state.listening = true;
    const micBtn = document.getElementById("btn-mic");
    if (micBtn) micBtn.classList.add("active");
    setReactor("listening", "Tıńlap atırman");
    setCaption("", "");

    const AudioContextCls = window.AudioContext || window.webkitAudioContext;
    state.audioCtx = new AudioContextCls();
    const source = state.audioCtx.createMediaStreamSource(state.mic);
    state.analyser = state.audioCtx.createAnalyser();
    state.analyser.fftSize = 512;
    source.connect(state.analyser);

    const dataArray = new Uint8Array(state.analyser.frequencyBinCount);
    state.silenceStartedAt = null;
    state.hasSpoken = false;
    state.listenStartedAt = performance.now();

    let mimeType = "audio/webm";
    if (window.MediaRecorder && MediaRecorder.isTypeSupported && !MediaRecorder.isTypeSupported(mimeType)) {
      mimeType = "";
    }
    state.recorder = new MediaRecorder(state.mic, mimeType ? { mimeType: mimeType } : undefined);
    state.chunks = [];
    state.recorder.addEventListener("dataavailable", (e) => {
      if (e.data && e.data.size > 0) state.chunks.push(e.data);
    });
    state.recorder.addEventListener("stop", () => {
      const blob = new Blob(state.chunks, { type: (state.recorder && state.recorder.mimeType) || "audio/webm" });
      state.chunks = [];
      if (blob.size > 800) {
        sendAudio(blob);
      } else {
        setReactor(null, "Tayar");
      }
    });
    state.recorder.start();

    // Audio-deńgey tekseriw setInterval penen — requestAnimationFrame EMES,
    // sebebi RAF fon (background) bette toqtaydı, al setInterval toqtamaydı.
    state.levelInterval = setInterval(() => {
      if (!state.analyser) return;
      state.analyser.getByteTimeDomainData(dataArray);
      let sumSquares = 0;
      for (let i = 0; i < dataArray.length; i++) {
        const v = (dataArray[i] - 128) / 128;
        sumSquares += v * v;
      }
      const level = Math.sqrt(sumSquares / dataArray.length);
      const now = performance.now();
      if (level >= SILENCE_THRESHOLD) {
        state.hasSpoken = true;
        state.silenceStartedAt = null;
        return;
      }
      // Sóylew ele baslanbaǵan bolsa — húrmet waqtın sanamaymız, tek ulıwma
      // waqıt sheginen (SPEECH_TIMEOUT_MS) asqanda mikrofondı jabamız, bolmasa
      // oylanıp turǵan iyeni mikrofon "esitpey" toqtatıp qoyar edi.
      if (!state.hasSpoken) {
        if (now - state.listenStartedAt > SPEECH_TIMEOUT_MS) stopMic();
        return;
      }
      if (state.silenceStartedAt === null) state.silenceStartedAt = now;
      if (now - state.silenceStartedAt > SILENCE_MS) {
        stopMic();
      }
    }, LEVEL_POLL_MS);
  }

  function toggleMic() {
    if (state.listening) {
      stopMic();
      setReactor(null, "Tayar");
    } else {
      startMic();
    }
  }

  function toggleMute(btnEl) {
    state.muted = !state.muted;
    if (state.muted) stopSpeaking();
    if (btnEl) btnEl.classList.toggle("active", state.muted);
  }

  // Barge-in: mikrofon túymesi, Space yamasa Esc — sóylep atırǵan dawıstı
  // derew toqtatadı ("mic goes deaf while it speaks" mashqalasınıń sheshimi)
  window.addEventListener("keydown", (e) => {
    const tag = e.target && e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA") return;
    if (e.code === "Space") {
      e.preventDefault();
      if (state.currentAudio) {
        stopSpeaking();
        setReactor(null, "Tayar");
      } else {
        toggleMic();
      }
    } else if (e.code === "Escape") {
      stopSpeaking();
      if (state.listening) stopMic();
      setReactor(null, "Tayar");
    }
  });

  window.JarvisVoice = {
    toggleMic: toggleMic,
    toggleMute: toggleMute,
    speak: speak,
    stopSpeaking: stopSpeaking,
  };
})();
