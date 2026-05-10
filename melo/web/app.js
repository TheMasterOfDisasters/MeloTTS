const state = {
  status: null,
  defaults: { texts: {}, presets: {} },
  voices: [],
};

const el = {
  version: document.getElementById("version"),
  build: document.getElementById("build"),
  runtime: document.getElementById("runtime"),
  text: document.getElementById("text"),
  metrics: document.getElementById("metrics"),
  language: document.getElementById("language"),
  speaker: document.getElementById("speaker"),
  preset: document.getElementById("preset"),
  speed: document.getElementById("speed"),
  speedValue: document.getElementById("speed-value"),
  sdpRatio: document.getElementById("sdp-ratio"),
  sdpRatioValue: document.getElementById("sdp-ratio-value"),
  noiseScale: document.getElementById("noise-scale"),
  noiseScaleValue: document.getElementById("noise-scale-value"),
  noiseScaleW: document.getElementById("noise-scale-w"),
  noiseScaleWValue: document.getElementById("noise-scale-w-value"),
  statusPill: document.getElementById("status-pill"),
  audio: document.getElementById("audio"),
  download: document.getElementById("download"),
  voices: document.getElementById("voices"),
  generate: document.getElementById("generate"),
  sample: document.getElementById("sample"),
  normalize: document.getElementById("normalize"),
  refreshVoices: document.getElementById("refresh-voices"),
};

function setStatus(message, mode = "neutral") {
  el.statusPill.textContent = message;
  el.statusPill.className = "rounded-full px-3 py-1 text-xs font-medium";
  if (mode === "ok") el.statusPill.classList.add("bg-cyan-300", "text-slate-950");
  else if (mode === "error") el.statusPill.classList.add("bg-red-500", "text-white");
  else el.statusPill.classList.add("bg-slate-800", "text-slate-300");
}

async function getJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = data.detail || data.error || detail;
    } catch (_) {
      // Keep default detail.
    }
    throw new Error(detail);
  }
  return response.json();
}

function setOptions(select, values) {
  select.innerHTML = "";
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
}

function currentPayload() {
  return {
    text: el.text.value,
    language: el.language.value,
    speaker_id: el.speaker.value,
    speed: Number(el.speed.value),
    sdp_ratio: Number(el.sdpRatio.value),
    noise_scale: Number(el.noiseScale.value),
    noise_scale_w: Number(el.noiseScaleW.value),
  };
}

function updateRangeLabels() {
  el.speedValue.value = Number(el.speed.value).toFixed(2);
  el.sdpRatioValue.value = Number(el.sdpRatio.value).toFixed(2);
  el.noiseScaleValue.value = Number(el.noiseScale.value).toFixed(2);
  el.noiseScaleWValue.value = Number(el.noiseScaleW.value).toFixed(2);
}

function applyPreset(name) {
  const preset = state.defaults.presets[name];
  if (!preset) return;
  el.speed.value = preset.speed;
  el.sdpRatio.value = preset.sdp_ratio;
  el.noiseScale.value = preset.noise_scale;
  el.noiseScaleW.value = preset.noise_scale_w;
  updateRangeLabels();
}

function speakerListFor(language) {
  const voice = state.voices.find((item) => item.language === language);
  return voice ? voice.speakers : [];
}

function renderVoices() {
  el.voices.innerHTML = "";
  state.voices.forEach((voice) => {
    const card = document.createElement("div");
    card.className = "voice-card";
    const speakers = voice.speakers.length ? voice.speakers.join(", ") : "No speakers loaded";
    card.innerHTML = `<strong>${voice.language}</strong> <span class="text-xs text-slate-500">${voice.status}</span><p>${speakers}</p>`;
    el.voices.appendChild(card);
  });
}

async function refreshMetrics() {
  const payload = currentPayload();
  if (!payload.text.trim()) {
    el.metrics.textContent = "0 characters | 0 words | 0 segments";
    return;
  }
  try {
    const data = await getJson("/tts/metrics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const metrics = data.metrics;
    el.metrics.textContent = `${metrics.characters} characters | ${metrics.words} words | ${metrics.segments} segments`;
  } catch (_) {
    const words = payload.text.trim().split(/\s+/).filter(Boolean).length;
    el.metrics.textContent = `${payload.text.length} characters | ${words} words`;
  }
}

async function refreshVoices() {
  const data = await getJson("/tts/voices");
  state.voices = data.voices;
  renderVoices();
}

async function onLanguageChange() {
  const language = el.language.value;
  setOptions(el.speaker, speakerListFor(language));
  if (!el.text.value.trim()) {
    el.text.value = state.defaults.texts[language] || "";
  }
  await refreshMetrics();
}

async function generateAudio() {
  const payload = currentPayload();
  if (!payload.text.trim()) {
    setStatus("Text is empty", "error");
    return;
  }
  setStatus("Generating...");
  el.generate.disabled = true;
  try {
    const response = await fetch("/tts/convert/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const data = await response.json();
        detail = data.detail || data.error || detail;
      } catch (_) {
        // Keep default detail.
      }
      throw new Error(detail);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    el.audio.src = url;
    el.download.href = url;
    el.download.classList.remove("hidden");
    setStatus("Generated", "ok");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    el.generate.disabled = false;
  }
}

async function init() {
  setStatus("Loading...");
  state.status = await getJson("/tts/status");
  state.defaults = await getJson("/tts/defaults");
  await refreshVoices();

  el.version.textContent = state.status.version;
  el.build.textContent = state.status.build_id;
  el.runtime.textContent = state.status.runtime;

  setOptions(el.language, state.status.loaded_languages);
  setOptions(el.preset, Object.keys(state.defaults.presets));
  el.language.value = state.status.loaded_languages[0] || "EN";
  el.preset.value = "Balanced";
  el.text.value = state.defaults.texts[el.language.value] || "";
  applyPreset(el.preset.value);
  await onLanguageChange();
  setStatus("Ready", "ok");
}

el.language.addEventListener("change", onLanguageChange);
el.preset.addEventListener("change", () => applyPreset(el.preset.value));
el.text.addEventListener("input", refreshMetrics);
el.sample.addEventListener("click", async () => {
  el.text.value = state.defaults.texts[el.language.value] || "";
  await refreshMetrics();
});
el.normalize.addEventListener("click", async () => {
  el.text.value = el.text.value.replace(/\s+/g, " ").trim();
  await refreshMetrics();
});
el.refreshVoices.addEventListener("click", refreshVoices);
el.generate.addEventListener("click", generateAudio);
[el.speed, el.sdpRatio, el.noiseScale, el.noiseScaleW].forEach((input) => {
  input.addEventListener("input", updateRangeLabels);
});

init().catch((error) => setStatus(error.message, "error"));
