(() => {
  const $ = (selector) => document.querySelector(selector);
  const state = {
    maxText: 3800,
    apiKeyRequired: false,
    browserSessionAuthenticated: false,
    browserUser: null,
    currentUrl: null,
    currentBlob: null,
    currentFilename: "audio.mp3",
    currentCacheId: null,
    voiceName: "Cô Gái Hoạt Ngôn",
    providerLabel: "",
    currentProviderLabel: "",
    voices: [],
    selectedVoice: null,
    queue: [],
    queueRunning: false,
    projectName: "story",
  };

  const elements = {
    text: $("#textInput"),
    charCount: $("#charCount"),
    rate: $("#rateInput"),
    rateOutput: $("#rateOutput"),
    filename: $("#filenameInput"),
    voiceSelect: $("#voiceSelect"),
    apiKey: $("#apiKeyInput"),
    securityDetails: $("#securityDetails"),
    toggleKey: $("#toggleKeyBtn"),
    generate: $("#generateBtn"),
    generateText: $("#generateText"),
    message: $("#formMessage"),
    status: $("#serverStatus"),
    currentUser: $("#currentUser"),
    logout: $("#logoutBtn"),
    voice: $("#voiceName"),
    voiceProvider: $("#voiceProviderInfo"),
    emptyPlayer: $("#emptyPlayer"),
    playerWrap: $("#audioPlayerWrap"),
    player: $("#audioPlayer"),
    cacheBadge: $("#cacheBadge"),
    currentFileName: $("#currentFileName"),
    currentMeta: $("#currentMeta"),
    download: $("#downloadBtn"),
    copyLink: $("#copyLinkBtn"),
    projectName: $("#projectNameInput"),
    preset: $("#presetSelect"),
    chunkSize: $("#chunkSizeInput"),
    dictionary: $("#dictionaryInput"),
    buildQueue: $("#buildQueueBtn"),
    previewSelection: $("#previewSelectionBtn"),
    generateQueue: $("#generateQueueBtn"),
    downloadMerged: $("#downloadMergedBtn"),
    bgm: $("#bgmInput"),
    bgmVolume: $("#bgmVolumeInput"),
    bgmVolumeOutput: $("#bgmVolumeOutput"),
    subtitleMode: $("#subtitleModeSelect"),
    subtitleDensity: $("#subtitleDensitySelect"),
    downloadBgmMix: $("#downloadBgmMixBtn"),
    exportSrt: $("#exportSrtBtn"),
    exportAss: $("#exportAssBtn"),
    exportTimeline: $("#exportTimelineBtn"),
    exportTikTokPack: $("#exportTikTokPackBtn"),
    queueSection: $("#queueSection"),
    queueSummary: $("#queueSummary"),
    queueList: $("#queueList"),
    queueTemplate: $("#queueTemplate"),
    clearQueue: $("#clearQueueBtn"),
    historyList: $("#historyList"),
    historyEmpty: $("#historyEmpty"),
    historyTemplate: $("#historyTemplate"),
    clearCache: $("#clearCacheBtn"),
  };

  const PRESETS = {
    movie_drama: { rate: 1.0, chunkSize: 2600, bgm: 20, subtitleMode: "sentence", density: "medium", pause: 0.25, hashtag: "#reviewphim #phimhay #drama #storytelling" },
    romance_story: { rate: 0.95, chunkSize: 3000, bgm: 16, subtitleMode: "sentence", density: "medium", pause: 0.35, hashtag: "#kechuyen #tamsu #tinhcam #storytime" },
    horror_mystery: { rate: 0.92, chunkSize: 2600, bgm: 24, subtitleMode: "sentence", density: "short", pause: 0.55, hashtag: "#kinhdi #bian #reviewphim #storytelling" },
    breaking_news: { rate: 1.08, chunkSize: 2200, bgm: 12, subtitleMode: "sentence", density: "short", pause: 0.15, hashtag: "#tinnong #bantin #news #capnhat" },
    late_night: { rate: 0.9, chunkSize: 3000, bgm: 15, subtitleMode: "sentence", density: "medium", pause: 0.5, hashtag: "#tamsu #demkhuya #kechuyen #radio" },
    long_series: { rate: 0.96, chunkSize: 3400, bgm: 18, subtitleMode: "chunk", density: "medium", pause: 0.45, hashtag: "#truyenaudio #truyendai #storytelling #series" },
    sales_hook: { rate: 1.12, chunkSize: 1800, bgm: 14, subtitleMode: "sentence", density: "short", pause: 0.12, hashtag: "#banhang #quangcao #tiktokshop #viral" },
  };

  const EMOTION_TAGS = {
    "bình thường": { rate: 1, pause: 0.25, label: "Bình thường" },
    "binh thuong": { rate: 1, pause: 0.25, label: "Bình thường" },
    "căng thẳng": { rate: 0.96, pause: 0.45, label: "Căng thẳng" },
    "cang thang": { rate: 0.96, pause: 0.45, label: "Căng thẳng" },
    "buồn": { rate: 0.9, pause: 0.55, label: "Buồn" },
    "buon": { rate: 0.9, pause: 0.55, label: "Buồn" },
    "phẫn nộ": { rate: 1.08, pause: 0.25, label: "Phẫn nộ" },
    "phan no": { rate: 1.08, pause: 0.25, label: "Phẫn nộ" },
    "thì thầm": { rate: 0.86, pause: 0.65, label: "Thì thầm" },
    "thi tham": { rate: 0.86, pause: 0.65, label: "Thì thầm" },
    "cao trào": { rate: 1.06, pause: 0.2, label: "Cao trào" },
    "cao trao": { rate: 1.06, pause: 0.2, label: "Cao trào" },
    "bí ẩn": { rate: 0.88, pause: 0.7, label: "Bí ẩn" },
    "bi an": { rate: 0.88, pause: 0.7, label: "Bí ẩn" },
    "chậm lại": { rate: 0.82, pause: 0.75, label: "Chậm lại" },
    "cham lai": { rate: 0.82, pause: 0.75, label: "Chậm lại" },
    "nhấn mạnh": { rate: 0.9, pause: 0.65, label: "Nhấn mạnh" },
    "nhan manh": { rate: 0.9, pause: 0.65, label: "Nhấn mạnh" },
  };

  function apiKey() {
    return elements.apiKey.value.trim();
  }

  function authHeaders(extra = {}) {
    const headers = { ...extra };
    if (apiKey() && !state.browserSessionAuthenticated) headers["X-API-Key"] = apiKey();
    return headers;
  }

  function setMessage(message = "", kind = "") {
    elements.message.textContent = message;
    elements.message.className = `form-message ${kind}`.trim();
  }

  function updateCount() {
    const length = elements.text.value.length;
    elements.charCount.textContent = `${length.toLocaleString("vi-VN")} ký tự`;
    elements.charCount.style.color = length > state.maxText * 0.92 ? "#ffca72" : "";
  }

  function updateRate() {
    elements.rateOutput.value = `${Number(elements.rate.value).toFixed(2)}×`;
    elements.rateOutput.textContent = `${Number(elements.rate.value).toFixed(2)}×`;
  }

  function setLoading(isLoading) {
    elements.generate.disabled = isLoading;
    elements.generate.classList.toggle("loading", isLoading);
    elements.generateText.textContent = isLoading ? "Đang tạo audio…" : "Tạo audio";
  }

  function contentDispositionFilename(value) {
    if (!value) return null;
    const utf8 = value.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8) return decodeURIComponent(utf8[1]);
    const simple = value.match(/filename="?([^";]+)"?/i);
    return simple ? simple[1] : null;
  }

  function decodeHeader(value) {
    if (!value) return "";
    try { return decodeURIComponent(value); }
    catch { return value; }
  }

  function escapeRegExp(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function safeSlug(value, fallback = "story") {
    const slug = value
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 72);
    return slug || fallback;
  }

  function voiceKey(voice) {
    return `${voice.provider}|${voice.voice_type}|${voice.resource_id}`;
  }

  function selectedVoicePayload() {
    if (!state.selectedVoice || state.selectedVoice.provider !== "capcut") return {};
    return {
      voice_type: state.selectedVoice.voice_type,
      resource_id: state.selectedVoice.resource_id,
      voice_name: state.selectedVoice.name,
    };
  }

  function applySelectedVoice(voice) {
    state.selectedVoice = voice || state.voices[0] || null;
    if (!state.selectedVoice) return;
    state.voiceName = state.selectedVoice.name || state.voiceName;
    state.providerLabel = state.selectedVoice.provider_label || state.providerLabel;
    elements.voice.textContent = state.voiceName;
    elements.voiceProvider.textContent = state.providerLabel;
    localStorage.setItem("voxSelectedVoice", voiceKey(state.selectedVoice));
  }

  function parseDictionary() {
    return elements.dictionary.value
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#"))
      .map((line) => {
        const separator = line.includes("=>") ? "=>" : "=";
        const index = line.indexOf(separator);
        if (index < 1) return null;
        return {
          from: line.slice(0, index).trim(),
          to: line.slice(index + separator.length).trim(),
        };
      })
      .filter((rule) => rule && rule.from);
  }

  function applyDictionary(text) {
    let output = text;
    for (const rule of parseDictionary()) {
      output = output.replace(new RegExp(escapeRegExp(rule.from), "g"), rule.to);
    }
    return output;
  }

  function normalizeTag(value) {
    return value
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/\s+/g, " ");
  }

  function readEmotionTag(text) {
    const match = text.trim().match(/^\[([^\]]+)\]\s*/);
    if (!match) return null;
    const rawTag = match[1].trim().toLowerCase();
    const emotion = EMOTION_TAGS[rawTag] || EMOTION_TAGS[normalizeTag(rawTag)] || null;
    if (!emotion) return null;
    return {
      marker: match[0],
      tag: `[${match[1].trim()}]`,
      emotion,
    };
  }

  function detectEmotionTag(text) {
    const trimmed = text.trim();
    const detected = readEmotionTag(trimmed);
    if (!detected) return { text: trimmed, emotion: null, tag: "" };
    return {
      text: trimmed.slice(detected.marker.length).trim(),
      emotion: detected.emotion,
      tag: detected.tag,
    };
  }

  function emotionRate(baseRate, emotion) {
    return Math.max(0.5, Math.min(2, Number(baseRate) * (emotion ? emotion.rate : 1)));
  }

  function splitEmotionBlocks(text) {
    const blocks = [];
    let current = [];
    const flush = () => {
      const value = current.join("\n").trim();
      if (value) blocks.push(value);
      current = [];
    };

    for (const rawLine of text.split("\n")) {
      const line = rawLine.trim();
      if (!line) {
        if (current.length) current.push("");
        continue;
      }
      if (readEmotionTag(line) && current.some((item) => item.trim())) {
        flush();
      }
      current.push(rawLine);
    }
    flush();
    return blocks.length ? blocks : [text.trim()];
  }

  function splitLongText(text, maxLength) {
    const clean = text.replace(/\u00a0/g, " ").replace(/\r\n/g, "\n").trim();
    if (!clean) return [];
    const chunks = [];
    const pushChunk = (value) => {
      const trimmed = value.replace(/\s+/g, " ").trim();
      if (trimmed) chunks.push(trimmed);
    };
    const withTag = (value, tagPrefix) => tagPrefix ? `${tagPrefix} ${value}` : value;
    const prefixedLength = (value, tagPrefix) => withTag(value, tagPrefix).length;
    const pushTaggedChunk = (value, tagPrefix) => pushChunk(withTag(value, tagPrefix));
    const splitParagraph = (paragraph, tagPrefix = "") => {
      const bodyMaxLength = Math.max(120, maxLength - (tagPrefix ? tagPrefix.length + 1 : 0));
      const sentences = paragraph
        .replace(/\s+/g, " ")
        .match(/[^.!?。！？…]+[.!?。！？…]*|.+/g) || [paragraph];
      let current = "";
      for (const sentenceRaw of sentences) {
        const sentence = sentenceRaw.trim();
        if (!sentence) continue;
        if ((current + " " + sentence).trim().length <= bodyMaxLength) {
          current = (current + " " + sentence).trim();
          continue;
        }
        if (current) pushTaggedChunk(current, tagPrefix);
        if (sentence.length <= bodyMaxLength) {
          current = sentence;
        } else {
          for (let start = 0; start < sentence.length; start += bodyMaxLength) {
            pushTaggedChunk(sentence.slice(start, start + bodyMaxLength), tagPrefix);
          }
          current = "";
        }
      }
      if (current) pushTaggedChunk(current, tagPrefix);
    };

    for (const block of splitEmotionBlocks(clean)) {
      const detected = detectEmotionTag(block);
      const tagPrefix = detected.emotion ? detected.tag : "";
      const body = detected.emotion ? detected.text : block.trim();
      if (!body) continue;

      let current = "";
      const flushCurrent = () => {
        if (current) pushTaggedChunk(current, tagPrefix);
        current = "";
      };

      for (const paragraph of body.split(/\n{2,}/).map((item) => item.trim()).filter(Boolean)) {
        const next = (current + "\n\n" + paragraph).trim();
        if (prefixedLength(next, tagPrefix) <= maxLength) {
          current = next;
        } else {
          flushCurrent();
          if (prefixedLength(paragraph, tagPrefix) <= maxLength) current = paragraph;
          else splitParagraph(paragraph, tagPrefix);
        }
      }
      flushCurrent();
    }
    return chunks;
  }

  function prepareSingleTtsInput(text, baseRate) {
    const clean = text.replace(/\u00a0/g, " ").replace(/\r\n/g, "\n").trim();
    let firstEmotion = null;
    let emotionCount = 0;
    const body = splitEmotionBlocks(clean)
      .map((block) => {
        const detected = detectEmotionTag(block);
        if (!detected.emotion) return block.trim();
        emotionCount += 1;
        if (!firstEmotion) firstEmotion = detected.emotion;
        return detected.text;
      })
      .filter(Boolean)
      .join("\n\n");
    return {
      text: body || clean,
      rate: emotionRate(baseRate, firstEmotion),
      emotion: firstEmotion,
      emotionCount,
    };
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 800);
  }

  function updateBgmVolume() {
    elements.bgmVolumeOutput.value = `${elements.bgmVolume.value}%`;
    elements.bgmVolumeOutput.textContent = `${elements.bgmVolume.value}%`;
  }

  function getDoneQueueItems() {
    return state.queue.filter((item) => item.blob);
  }

  function createAudioContext() {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) throw new Error("Trình duyệt không hỗ trợ Web Audio API.");
    return new AudioContextClass();
  }

  async function decodeBlobToBuffer(audioContext, blob) {
    const data = await blob.arrayBuffer();
    return audioContext.decodeAudioData(data.slice(0));
  }

  function sentenceParts(text) {
    const matches = text
      .replace(/\s+/g, " ")
      .trim()
      .match(/[^.!?。！？…]+[.!?。！？…]*|.+/g);
    return (matches || [text]).map((part) => part.trim()).filter(Boolean);
  }

  function subtitleParts(text) {
    if (elements.subtitleMode.value === "chunk") return [text.replace(/\s+/g, " ").trim()];
    const words = text.replace(/\s+/g, " ").trim().split(" ").filter(Boolean);
    if (!words.length) return [];
    const density = elements.subtitleDensity.value;
    const maxWords = density === "short" ? 4 : density === "medium" ? 7 : 6;
    const keywords = new Set(["nhưng", "bất", "ngờ", "không", "sự", "thật", "bí", "mật", "đột", "nhiên"]);
    const parts = [];
    let current = [];
    for (const word of words) {
      current.push(word);
      const normalized = word.toLowerCase().replace(/[^\wÀ-ỹ]+/g, "");
      const shouldBreak = current.length >= maxWords || (density === "auto" && current.length >= 3 && keywords.has(normalized));
      if (shouldBreak) {
        parts.push(current.join(" "));
        current = [];
      }
    }
    if (current.length) parts.push(current.join(" "));
    return parts;
  }

  function srtTime(seconds) {
    const totalMs = Math.max(0, Math.round(seconds * 1000));
    const hours = Math.floor(totalMs / 3600000);
    const minutes = Math.floor((totalMs % 3600000) / 60000);
    const secs = Math.floor((totalMs % 60000) / 1000);
    const millis = totalMs % 1000;
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")},${String(millis).padStart(3, "0")}`;
  }

  function assTime(seconds) {
    const totalCs = Math.max(0, Math.round(seconds * 100));
    const hours = Math.floor(totalCs / 360000);
    const minutes = Math.floor((totalCs % 360000) / 6000);
    const secs = Math.floor((totalCs % 6000) / 100);
    const centis = totalCs % 100;
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}.${String(centis).padStart(2, "0")}`;
  }

  function escapeAss(value) {
    return value.replace(/[{}]/g, "").replace(/\n/g, "\\N");
  }

  function karaokeAssText(text, duration) {
    const words = text.replace(/\s+/g, " ").trim().split(" ").filter(Boolean);
    if (!words.length) return "";
    const totalChars = Math.max(1, words.reduce((sum, word) => sum + word.length, 0));
    return words.map((word) => {
      const centis = Math.max(8, Math.round(duration * 100 * (word.length / totalChars)));
      const clean = escapeAss(word);
      const emphasis = /^(nhưng|bất|ngờ|không|sự|thật|bí|mật)$/i.test(clean) ? "{\\c&H00D7FF&}" : "";
      return `{\\k${centis}}${emphasis}${clean}`;
    }).join(" ");
  }

  async function ensureQueueDurations(items = getDoneQueueItems()) {
    const audioContext = createAudioContext();
    try {
      for (const item of items) {
        if (!item.duration) {
          const buffer = await decodeBlobToBuffer(audioContext, item.blob);
          item.duration = buffer.duration;
        }
      }
    } finally {
      audioContext.close().catch(() => undefined);
    }
  }

  function buildTimelineItems() {
    const items = getDoneQueueItems();
    const timeline = [];
    let cursor = 0;
    for (const item of items) {
      const duration = Math.max(0.1, Number(item.duration) || 0.1);
      const parts = elements.subtitleMode.value === "chunk"
        ? [item.text]
        : sentenceParts(item.text).flatMap((sentence) => subtitleParts(sentence));
      const totalChars = Math.max(1, parts.reduce((sum, part) => sum + part.length, 0));
      let localCursor = cursor;
      for (let index = 0; index < parts.length; index += 1) {
        const part = parts[index];
        const sliceDuration = index === parts.length - 1
          ? cursor + duration - localCursor
          : Math.max(0.45, duration * (part.length / totalChars));
        timeline.push({
          start: localCursor,
          end: localCursor + sliceDuration,
          text: part,
          part: item.index,
          emotion: item.emotionLabel || "Bình thường",
        });
        localCursor += sliceDuration;
      }
      cursor += duration + (Number(item.pauseAfter) || 0);
    }
    return timeline;
  }

  function buildSrt(timeline) {
    return timeline.map((item, index) => {
      const text = item.text.replace(/\s+/g, " ").trim();
      return `${index + 1}\n${srtTime(item.start)} --> ${srtTime(item.end)}\n${text}\n`;
    }).join("\n");
  }

  function buildAss(timeline) {
    const preset = elements.preset.value;
    const primary = preset === "horror_mystery" ? "&H00FFFFFF" : preset === "breaking_news" ? "&H0000FFFF" : "&H00FFFFFF";
    const secondary = preset === "horror_mystery" ? "&H002020FF" : "&H0000D7FF";
    const outline = preset === "late_night" ? "&H00604030" : "&H00000000";
    const fontSize = preset === "breaking_news" ? 62 : 54;
    const events = timeline.map((item) => {
      const text = karaokeAssText(item.text, Math.max(0.1, item.end - item.start));
      return `Dialogue: 0,${assTime(item.start)},${assTime(item.end)},Default,,0,0,80,,${text}`;
    }).join("\n");
    return `[Script Info]
Title: ${state.projectName || "Vox Local Story TTS"}
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,${fontSize},${primary},${secondary},${outline},&H64000000,-1,0,0,0,100,100,0,0,1,4,1,2,70,70,190,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
${events}
`;
  }

  function interleaveToWav(audioBuffer) {
    const channels = Math.min(2, audioBuffer.numberOfChannels);
    const sampleRate = audioBuffer.sampleRate;
    const length = audioBuffer.length;
    const bytesPerSample = 2;
    const blockAlign = channels * bytesPerSample;
    const buffer = new ArrayBuffer(44 + length * blockAlign);
    const view = new DataView(buffer);
    const writeString = (offset, value) => {
      for (let index = 0; index < value.length; index += 1) view.setUint8(offset + index, value.charCodeAt(index));
    };
    writeString(0, "RIFF");
    view.setUint32(4, 36 + length * blockAlign, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, channels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * blockAlign, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bytesPerSample * 8, true);
    writeString(36, "data");
    view.setUint32(40, length * blockAlign, true);
    let offset = 44;
    const channelData = Array.from({ length: channels }, (_, index) => audioBuffer.getChannelData(index));
    for (let sample = 0; sample < length; sample += 1) {
      for (let channel = 0; channel < channels; channel += 1) {
        const raw = Math.max(-1, Math.min(1, channelData[channel][sample]));
        view.setInt16(offset, raw < 0 ? raw * 0x8000 : raw * 0x7fff, true);
        offset += 2;
      }
    }
    return new Blob([buffer], { type: "audio/wav" });
  }

  function crc32(bytes) {
    let crc = 0xffffffff;
    for (const byte of bytes) {
      crc ^= byte;
      for (let bit = 0; bit < 8; bit += 1) {
        crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
      }
    }
    return (crc ^ 0xffffffff) >>> 0;
  }

  function dosDateTime(date = new Date()) {
    const time = (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2);
    const dosDate = ((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
    return { time, dosDate };
  }

  async function createZip(files) {
    const encoder = new TextEncoder();
    const localParts = [];
    const centralParts = [];
    let offset = 0;
    const { time, dosDate } = dosDateTime();
    for (const file of files) {
      const nameBytes = encoder.encode(file.name);
      const data = file.data instanceof Blob
        ? new Uint8Array(await file.data.arrayBuffer())
        : encoder.encode(String(file.data));
      const crc = crc32(data);
      const local = new ArrayBuffer(30 + nameBytes.length);
      const localView = new DataView(local);
      localView.setUint32(0, 0x04034b50, true);
      localView.setUint16(4, 20, true);
      localView.setUint16(6, 0, true);
      localView.setUint16(8, 0, true);
      localView.setUint16(10, time, true);
      localView.setUint16(12, dosDate, true);
      localView.setUint32(14, crc, true);
      localView.setUint32(18, data.length, true);
      localView.setUint32(22, data.length, true);
      localView.setUint16(26, nameBytes.length, true);
      new Uint8Array(local, 30).set(nameBytes);
      localParts.push(local, data);

      const central = new ArrayBuffer(46 + nameBytes.length);
      const centralView = new DataView(central);
      centralView.setUint32(0, 0x02014b50, true);
      centralView.setUint16(4, 20, true);
      centralView.setUint16(6, 20, true);
      centralView.setUint16(8, 0, true);
      centralView.setUint16(10, 0, true);
      centralView.setUint16(12, time, true);
      centralView.setUint16(14, dosDate, true);
      centralView.setUint32(16, crc, true);
      centralView.setUint32(20, data.length, true);
      centralView.setUint32(24, data.length, true);
      centralView.setUint16(28, nameBytes.length, true);
      centralView.setUint32(42, offset, true);
      new Uint8Array(central, 46).set(nameBytes);
      centralParts.push(central);
      offset += local.byteLength + data.length;
    }
    const centralSize = centralParts.reduce((sum, part) => sum + part.byteLength, 0);
    const end = new ArrayBuffer(22);
    const endView = new DataView(end);
    endView.setUint32(0, 0x06054b50, true);
    endView.setUint16(8, files.length, true);
    endView.setUint16(10, files.length, true);
    endView.setUint32(12, centralSize, true);
    endView.setUint32(16, offset, true);
    return new Blob([...localParts, ...centralParts, end], { type: "application/zip" });
  }

  async function mixQueueWithBgm() {
    const items = getDoneQueueItems();
    if (!items.length) throw new Error("Chưa có audio trong queue.");
    const bgmFile = elements.bgm.files && elements.bgm.files[0];
    if (!bgmFile) throw new Error("Hãy chọn file nhạc nền trước.");
    const context = createAudioContext();
    try {
      const voiceBuffers = [];
      for (const item of items) {
        const buffer = await decodeBlobToBuffer(context, item.blob);
        item.duration = buffer.duration;
        voiceBuffers.push(buffer);
      }
      const bgmBuffer = await context.decodeAudioData(await bgmFile.arrayBuffer());
      const sampleRate = context.sampleRate;
      const channels = 2;
      const totalDuration = voiceBuffers.reduce((sum, buffer, index) => sum + buffer.duration + (Number(items[index].pauseAfter) || 0), 0);
      const frameCount = Math.ceil(totalDuration * sampleRate);
      const output = context.createBuffer(channels, frameCount, sampleRate);
      const voiceMask = new Uint8Array(frameCount);
      let writeOffset = 0;
      for (let bufferIndex = 0; bufferIndex < voiceBuffers.length; bufferIndex += 1) {
        const buffer = voiceBuffers[bufferIndex];
        for (let channel = 0; channel < channels; channel += 1) {
          const target = output.getChannelData(channel);
          const source = buffer.getChannelData(Math.min(channel, buffer.numberOfChannels - 1));
          for (let index = 0; index < source.length && writeOffset + index < target.length; index += 1) {
            target[writeOffset + index] += source[index] * 0.96;
            voiceMask[writeOffset + index] = 1;
          }
        }
        writeOffset += Math.round((buffer.duration + (Number(items[bufferIndex].pauseAfter) || 0)) * sampleRate);
      }
      const bgmVolume = Number(elements.bgmVolume.value) / 100;
      const fadeFrames = Math.min(Math.round(sampleRate * 2), frameCount);
      for (let channel = 0; channel < channels; channel += 1) {
        const target = output.getChannelData(channel);
        const bgm = bgmBuffer.getChannelData(Math.min(channel, bgmBuffer.numberOfChannels - 1));
        for (let index = 0; index < frameCount; index += 1) {
          const fadeIn = fadeFrames ? Math.min(1, index / fadeFrames) : 1;
          const fadeOut = fadeFrames ? Math.min(1, (frameCount - index) / fadeFrames) : 1;
          const duck = voiceMask[index] ? 0.42 : 1;
          const gain = bgmVolume * duck * Math.min(fadeIn, fadeOut);
          target[index] = Math.max(-1, Math.min(1, target[index] + bgm[index % bgm.length] * gain));
        }
      }
      return interleaveToWav(output);
    } finally {
      context.close().catch(() => undefined);
    }
  }

  function revokeCurrentUrl() {
    if (state.currentUrl) URL.revokeObjectURL(state.currentUrl);
    state.currentUrl = null;
  }

  function showAudio({ blob, filename, rate, cache, cacheId, voiceName, providerLabel, fallback }) {
    revokeCurrentUrl();
    state.currentBlob = blob;
    state.currentFilename = filename || "co_gai_hoat_ngon.mp3";
    state.currentUrl = URL.createObjectURL(blob);
    state.currentCacheId = cacheId || null;
    state.currentProviderLabel = providerLabel || state.providerLabel;

    elements.player.src = state.currentUrl;
    elements.currentFileName.textContent = state.currentFilename;
    const metaVoice = voiceName || state.voiceName;
    const providerText = state.currentProviderLabel ? ` · ${state.currentProviderLabel}` : "";
    elements.currentMeta.textContent = `${metaVoice} · ${Number(rate).toFixed(2)}×${providerText}`;
    elements.emptyPlayer.classList.add("hidden");
    elements.playerWrap.classList.remove("hidden");
    if (cache) {
      elements.cacheBadge.textContent = fallback
        ? "FALLBACK LOCAL"
        : cache === "HIT"
          ? "CACHE HIT"
          : "ĐÃ TẠO MỚI";
      elements.cacheBadge.className = `cache-badge ${cache === "HIT" ? "hit" : ""}`;
    } else {
      elements.cacheBadge.className = "cache-badge hidden";
    }
  }

  function downloadCurrent() {
    if (!state.currentBlob || !state.currentUrl) return;
    const link = document.createElement("a");
    link.href = state.currentUrl;
    link.download = state.currentFilename;
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  function applyPreset() {
    const preset = PRESETS[elements.preset.value] || PRESETS.movie_drama;
    elements.rate.value = preset.rate.toFixed(2);
    elements.chunkSize.value = String(preset.chunkSize);
    elements.bgmVolume.value = String(preset.bgm);
    elements.subtitleMode.value = preset.subtitleMode;
    elements.subtitleDensity.value = preset.density;
    updateRate();
    updateBgmVolume();
    localStorage.setItem("voxBgmVolume", elements.bgmVolume.value);
    localStorage.setItem("voxSubtitleMode", elements.subtitleMode.value);
    localStorage.setItem("voxSubtitleDensity", elements.subtitleDensity.value);
  }

  function queueStats() {
    const total = state.queue.length;
    const done = state.queue.filter((item) => item.status === "done").length;
    const error = state.queue.filter((item) => item.status === "error").length;
    return { total, done, error };
  }

  function updateQueueControls() {
    const { total, done, error } = queueStats();
    elements.generateQueue.disabled = state.queueRunning || (!total && !elements.text.value.trim());
    elements.downloadMerged.disabled = done < 1;
    elements.exportSrt.disabled = done < 1;
    elements.exportAss.disabled = done < 1;
    elements.exportTimeline.disabled = done < 1;
    elements.exportTikTokPack.disabled = done < 1;
    elements.downloadBgmMix.disabled = done < 1 || !(elements.bgm.files && elements.bgm.files[0]);
    elements.queueSummary.textContent = error
      ? `${done}/${total} xong · ${error} lỗi`
      : `${done}/${total} xong`;
    elements.queueSection.classList.toggle("hidden", total === 0);
  }

  function renderQueue() {
    elements.queueList.innerHTML = "";
    for (const item of state.queue) {
      const fragment = elements.queueTemplate.content.cloneNode(true);
      const row = fragment.querySelector(".queue-item");
      row.dataset.status = item.status;
      fragment.querySelector(".queue-index").textContent = String(item.index).padStart(2, "0");
      fragment.querySelector(".queue-preview").textContent = item.text;
      fragment.querySelector(".queue-meta").textContent = `${item.emotionLabel || "Bình thường"} · ${item.text.length.toLocaleString("vi-VN")} ký tự · ${Number(item.rate).toFixed(2)}× · nghỉ ${(item.pauseAfter || 0).toFixed(1)}s`;
      const status = fragment.querySelector(".queue-status");
      status.textContent = item.statusText || "Chờ";
      const generateButton = fragment.querySelector(".queue-generate");
      const playButton = fragment.querySelector(".queue-play");
      const downloadButton = fragment.querySelector(".queue-download");
      generateButton.disabled = item.status === "running" || (state.queueRunning && item.status !== "error");
      playButton.disabled = !item.blob;
      downloadButton.disabled = !item.blob;
      generateButton.addEventListener("click", async () => {
        await generateQueueItem(item.index - 1, true);
        renderQueue();
      });
      playButton.addEventListener("click", () => {
        if (!item.blob) return;
        showAudio({
          blob: item.blob,
          filename: item.filename,
          rate: item.rate,
          cache: item.cache,
          cacheId: item.cacheId,
          voiceName: item.voiceName,
          providerLabel: item.providerLabel,
        });
        elements.player.play().catch(() => undefined);
      });
      downloadButton.addEventListener("click", () => {
        if (item.blob) downloadBlob(item.blob, item.filename);
      });
      elements.queueList.appendChild(fragment);
    }
    updateQueueControls();
  }

  function buildQueue() {
    const source = elements.text.value.trim();
    if (!source) {
      setMessage("Hãy nhập truyện trước khi chia đoạn.", "error");
      elements.text.focus();
      return false;
    }
    const maxLength = Math.min(
      state.maxText,
      Math.max(800, Number(elements.chunkSize.value) || 3200)
    );
    elements.chunkSize.value = String(maxLength);
    const prepared = applyDictionary(source);
    const chunks = splitLongText(prepared, maxLength);
    if (!chunks.length) {
      setMessage("Không tạo được đoạn đọc từ nội dung hiện tại.", "error");
      return false;
    }
    state.projectName = safeSlug(elements.projectName.value || elements.filename.value || "story");
    const preset = PRESETS[elements.preset.value] || PRESETS.movie_drama;
    const baseRate = Number(elements.rate.value);
    state.queue = chunks.map((text, index) => {
      const detected = detectEmotionTag(text);
      const emotion = detected.emotion;
      const blockRate = emotionRate(baseRate, emotion);
      return {
        id: window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${index}`,
        index: index + 1,
        text: detected.text || text,
        rate: blockRate,
        emotionLabel: emotion ? emotion.label : "Bình thường",
        pauseAfter: emotion ? emotion.pause : preset.pause,
        status: "pending",
        statusText: "Chờ",
        blob: null,
        filename: `${state.projectName}_part_${String(index + 1).padStart(3, "0")}.mp3`,
        cacheId: null,
        cache: null,
        providerLabel: state.providerLabel,
        voiceName: state.voiceName,
        voice: state.selectedVoice,
      };
    });
    renderQueue();
    setMessage(`Đã chia thành ${chunks.length} đoạn đọc.`, "success");
    return true;
  }

  async function generateQueueItem(index, force = false) {
    const item = state.queue[index];
    if (!item || (item.blob && !force)) return item;
    item.status = "running";
    item.statusText = "Đang tạo";
    renderQueue();
    try {
      const response = await fetch("/v1/tts", {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          text: item.text,
          rate: item.rate,
          filename: item.filename,
          ...(item.voice && item.voice.provider === "capcut" ? {
            voice_type: item.voice.voice_type,
            resource_id: item.voice.resource_id,
            voice_name: item.voice.name,
          } : {}),
        }),
      });
      if (!response.ok) throw new Error(await parseError(response));
      const blob = await response.blob();
      const contentType = response.headers.get("content-type") || blob.type || "audio/mpeg";
      const extension = contentType.includes("wav") ? "wav" : contentType.includes("mpeg") || contentType.includes("mp3") ? "mp3" : "bin";
      item.blob = blob;
      item.filename = contentDispositionFilename(response.headers.get("content-disposition")) || item.filename.replace(/\.[^.]+$/, `.${extension}`);
      item.cache = response.headers.get("x-tts-cache");
      item.cacheId = response.headers.get("x-tts-cache-id");
      item.providerLabel = decodeHeader(response.headers.get("x-tts-provider-label")) || state.providerLabel;
      item.voiceName = decodeHeader(response.headers.get("x-tts-voice-name")) || state.voiceName;
      item.contentType = contentType;
      item.status = "done";
      item.statusText = item.cache === "HIT" ? "Cache" : "Xong";
      return item;
    } catch (error) {
      item.status = "error";
      item.statusText = "Lỗi";
      item.error = error.message || "Không tạo được audio.";
      setMessage(`Đoạn ${item.index}: ${item.error}`, "error");
      return item;
    } finally {
      renderQueue();
    }
  }

  async function generateQueueAll() {
    if (state.queueRunning) return;
    if (!state.queue.length && !buildQueue()) return;
    if (!state.queue.length) return;
    state.queueRunning = true;
    renderQueue();
    try {
      for (let index = 0; index < state.queue.length; index += 1) {
        const item = state.queue[index];
        if (item.status === "done" && item.blob) continue;
        setMessage(`Đang tạo đoạn ${item.index}/${state.queue.length}…`);
        await generateQueueItem(index);
        if (state.queue[index].status === "error") break;
      }
      const { done, total, error } = queueStats();
      setMessage(error ? `Queue dừng ở ${done}/${total} đoạn.` : `Đã tạo xong ${done}/${total} đoạn.`, error ? "error" : "success");
      await loadHistory();
    } finally {
      state.queueRunning = false;
      renderQueue();
    }
  }

  function downloadMergedQueue() {
    const done = state.queue.filter((item) => item.blob);
    if (!done.length) return;
    const merged = new Blob(done.map((item) => item.blob), { type: done[0].contentType || "audio/mpeg" });
    const extension = (done[0].contentType || "").includes("wav") ? "wav" : "mp3";
    downloadBlob(merged, `${state.projectName || "story"}_merged.${extension}`);
  }

  async function exportSrt() {
    const items = getDoneQueueItems();
    if (!items.length) return;
    setMessage("Đang tính timeline subtitle…");
    try {
      await ensureQueueDurations(items);
      const timeline = buildTimelineItems();
      downloadBlob(new Blob([buildSrt(timeline)], { type: "text/plain;charset=utf-8" }), `${state.projectName || "story"}.srt`);
      setMessage("Đã export file SRT.", "success");
    } catch (error) {
      setMessage(error.message || "Không thể export SRT.", "error");
    }
  }

  async function exportAss() {
    const items = getDoneQueueItems();
    if (!items.length) return;
    setMessage("Đang tạo subtitle ASS…");
    try {
      await ensureQueueDurations(items);
      const timeline = buildTimelineItems();
      downloadBlob(new Blob([buildAss(timeline)], { type: "text/plain;charset=utf-8" }), `${state.projectName || "story"}.ass`);
      setMessage("Đã export file ASS.", "success");
    } catch (error) {
      setMessage(error.message || "Không thể export ASS.", "error");
    }
  }

  async function exportTimelineJson() {
    const items = getDoneQueueItems();
    if (!items.length) return;
    setMessage("Đang tạo timeline JSON…");
    try {
      await ensureQueueDurations(items);
      const timeline = buildTimelineItems();
      const payload = {
        project: state.projectName || "story",
        voice: state.voiceName,
        provider: state.providerLabel,
        preset: elements.preset.value,
        subtitle_mode: elements.subtitleMode.value,
        subtitle_density: elements.subtitleDensity.value,
        total_duration: timeline.length ? timeline[timeline.length - 1].end : 0,
        items: timeline,
      };
      downloadBlob(
        new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" }),
        `${state.projectName || "story"}_timeline.json`
      );
      setMessage("Đã export timeline JSON.", "success");
    } catch (error) {
      setMessage(error.message || "Không thể export timeline.", "error");
    }
  }

  function buildContentPackText(timeline) {
    const firstText = timeline.map((item) => item.text).join(" ").replace(/\s+/g, " ").trim();
    const short = firstText.slice(0, 130);
    const preset = PRESETS[elements.preset.value] || PRESETS.movie_drama;
    return {
      caption: `${short}${firstText.length > 130 ? "..." : ""}\n\n${preset.hashtag}`,
      hashtags: preset.hashtag,
      thumbnail: [
        "Sự thật phía sau câu chuyện này",
        "Không ai ngờ kết cục lại như vậy",
        "Đừng bỏ qua 10 giây cuối",
        "Một bí mật khiến mọi thứ đảo chiều",
      ].join("\n"),
      scenePrompts: timeline.slice(0, 24).map((item, index) => {
        return `${String(index + 1).padStart(2, "0")}. ${item.text} | mood: ${item.emotion || "story"} | vertical cinematic frame`;
      }).join("\n"),
    };
  }

  async function exportTikTokPack() {
    const items = getDoneQueueItems();
    if (!items.length) return;
    setMessage("Đang đóng gói TikTok Pack…");
    elements.exportTikTokPack.disabled = true;
    try {
      await ensureQueueDurations(items);
      const timeline = buildTimelineItems();
      const mergedAudio = new Blob(items.map((item) => item.blob), { type: items[0].contentType || "audio/mpeg" });
      const timelinePayload = {
        project: state.projectName || "story",
        voice: state.voiceName,
        provider: state.providerLabel,
        preset: elements.preset.value,
        subtitle_mode: elements.subtitleMode.value,
        subtitle_density: elements.subtitleDensity.value,
        total_duration: timeline.length ? timeline[timeline.length - 1].end : 0,
        items: timeline,
      };
      const texts = buildContentPackText(timeline);
      const files = [
        { name: "audio.mp3", data: mergedAudio },
        { name: "subtitle.srt", data: buildSrt(timeline) },
        { name: "subtitle.ass", data: buildAss(timeline) },
        { name: "timeline.json", data: JSON.stringify(timelinePayload, null, 2) },
        { name: "caption.txt", data: texts.caption },
        { name: "hashtags.txt", data: texts.hashtags },
        { name: "thumbnail-text.txt", data: texts.thumbnail },
        { name: "scene-prompts.txt", data: texts.scenePrompts },
      ];
      const zip = await createZip(files);
      downloadBlob(zip, `${state.projectName || "story"}_tiktok_pack.zip`);
      setMessage("Đã export TikTok Pack.", "success");
    } catch (error) {
      setMessage(error.message || "Không thể export TikTok Pack.", "error");
    } finally {
      updateQueueControls();
    }
  }

  async function downloadBgmMix() {
    setMessage("Đang mix nhạc nền trong trình duyệt…");
    elements.downloadBgmMix.disabled = true;
    try {
      const wav = await mixQueueWithBgm();
      downloadBlob(wav, `${state.projectName || "story"}_with_bgm.wav`);
      setMessage("Đã export WAV có nhạc nền.", "success");
    } catch (error) {
      setMessage(error.message || "Không thể mix nhạc nền.", "error");
    } finally {
      updateQueueControls();
    }
  }

  function clearQueue() {
    state.queue = [];
    renderQueue();
    setMessage("Đã xóa queue hiện tại.");
  }

  async function ensureConfig() {
    try {
      const response = await fetch("/api/ui/config", { cache: "no-store" });
      if (!response.ok) throw new Error("Không thể kiểm tra server.");
      const config = await response.json();
      state.maxText = config.max_text_length || 3800;
      elements.text.removeAttribute("maxlength");
      elements.chunkSize.max = state.maxText;
      if (Number(elements.chunkSize.value) > state.maxText) elements.chunkSize.value = String(state.maxText);
      state.voiceName = config.voice || "Cô Gái Hoạt Ngôn";
      state.providerLabel = config.provider_label || "";
      elements.voice.textContent = state.voiceName;
      elements.voiceProvider.textContent = state.providerLabel || "Provider local";
      state.browserSessionAuthenticated = Boolean(config.browser_session_authenticated);
      state.browserUser = config.browser_user || null;
      state.apiKeyRequired = Boolean(config.api_key_required && !state.browserSessionAuthenticated);
      if (elements.currentUser) {
        const userLabel = state.browserUser
          ? (state.browserUser.email || state.browserUser.label || state.browserUser.sub || "Đã đăng nhập")
          : "";
        elements.currentUser.textContent = userLabel;
        elements.currentUser.classList.toggle("hidden", !state.browserSessionAuthenticated);
      }
      if (elements.logout) elements.logout.classList.toggle("hidden", !state.browserSessionAuthenticated);
      elements.securityDetails.open = state.apiKeyRequired || Boolean(apiKey());
      if (config.server_status === "ok") {
        elements.status.textContent = config.provider === "local" ? "Local offline sẵn sàng" : "Server sẵn sàng";
        elements.status.className = "status-pill status-ready";
      } else {
        elements.status.textContent = "Cần cấu hình provider";
        elements.status.className = "status-pill status-problem";
      }
      updateCount();
      return config;
    } catch (error) {
      elements.status.textContent = "Không kết nối được server";
      elements.status.className = "status-pill status-problem";
      setMessage(error.message, "error");
      return null;
    }
  }

  async function loadVoices() {
    try {
      const response = await fetch("/v1/voices", { cache: "no-store" });
      if (!response.ok) throw new Error("Không tải được danh sách voice.");
      const voices = await response.json();
      state.voices = voices.filter((voice) => voice.provider === "capcut");
      if (!state.voices.length) state.voices = voices;
      elements.voiceSelect.innerHTML = "";
      const saved = localStorage.getItem("voxSelectedVoice");
      let selected = null;
      for (const voice of state.voices) {
        const option = document.createElement("option");
        option.value = voiceKey(voice);
        option.textContent = `${voice.name} · ${voice.language || "vi-VN"}`;
        option.dataset.voiceType = voice.voice_type;
        option.dataset.resourceId = voice.resource_id;
        elements.voiceSelect.appendChild(option);
        if (saved && saved === option.value) selected = voice;
        if (!selected && voice.voice_type === "BV074_streaming" && voice.resource_id === "7102355709945188865") selected = voice;
      }
      applySelectedVoice(selected || state.voices[0]);
      if (state.selectedVoice) elements.voiceSelect.value = voiceKey(state.selectedVoice);
    } catch (error) {
      setMessage(error.message, "error");
    }
  }

  async function parseError(response) {
    try {
      const data = await response.json();
      return data.detail || "Server trả về lỗi không xác định.";
    } catch {
      return `Yêu cầu thất bại (HTTP ${response.status}).`;
    }
  }

  async function generate() {
    const text = elements.text.value.trim();
    if (!text) {
      setMessage("Hãy nhập nội dung cần đọc trước khi tạo audio.", "error");
      elements.text.focus();
      return;
    }
    const prepared = prepareSingleTtsInput(applyDictionary(text), Number(elements.rate.value));
    if (prepared.text.length > state.maxText) {
      setMessage(`Một lần tạo chỉ tối đa ${state.maxText.toLocaleString("vi-VN")} ký tự. Hãy dùng Chia đoạn để tạo queue.`, "error");
      return;
    }
    if (state.apiKeyRequired && !apiKey()) {
      setMessage("Server yêu cầu X-API-Key. Hãy mở “Thiết lập truy cập local” và nhập key trong .env.", "error");
      elements.securityDetails.open = true;
      elements.apiKey.focus();
      return;
    }

    setLoading(true);
    setMessage("Đang gửi nội dung đến provider TTS. Lần đầu có thể chờ tạo audio…");
    try {
      const response = await fetch("/v1/tts", {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          text: prepared.text,
          rate: prepared.rate,
          filename: elements.filename.value.trim() || (elements.projectName.value.trim() ? `${safeSlug(elements.projectName.value)}.mp3` : null),
          ...selectedVoicePayload(),
        }),
      });
      if (!response.ok) throw new Error(await parseError(response));
      const blob = await response.blob();
      const filename = contentDispositionFilename(response.headers.get("content-disposition")) || elements.filename.value.trim() || "co_gai_hoat_ngon.mp3";
      const cache = response.headers.get("x-tts-cache");
      const cacheId = response.headers.get("x-tts-cache-id");
      const providerLabel = decodeHeader(response.headers.get("x-tts-provider-label")) || state.providerLabel;
      const voiceName = decodeHeader(response.headers.get("x-tts-voice-name")) || state.voiceName;
      const fallback = response.headers.get("x-tts-fallback") === "true";
      showAudio({ blob, filename, rate: prepared.rate, cache, cacheId, voiceName, providerLabel, fallback });
      if (fallback) {
        setMessage("Provider CapCut lỗi nên app đã dùng fallback local và lưu cache.", "success");
      } else if (prepared.emotionCount > 1) {
        setMessage("Audio đơn đã bỏ emotion tag và dùng nhịp của tag đầu. Muốn đổi cảm xúc từng block, hãy dùng Chia đoạn rồi Tạo tất cả.", "success");
      } else if (prepared.emotion) {
        setMessage(`Đã áp dụng tag ${prepared.emotion.label} cho audio.`, "success");
      } else {
        setMessage(cache === "HIT" ? "Đã lấy audio từ cache local." : "Audio đã tạo xong và lưu vào cache local.", "success");
      }
      await loadHistory();
    } catch (error) {
      setMessage(error.message || "Không thể tạo audio.", "error");
    } finally {
      setLoading(false);
    }
  }

  async function previewSelection() {
    const start = elements.text.selectionStart || 0;
    const end = elements.text.selectionEnd || 0;
    const selected = elements.text.value.slice(start, end).trim();
    const text = selected || elements.text.value.trim().split(/\n{2,}/).find(Boolean) || "";
    if (!text) {
      setMessage("Hãy bôi chọn một câu hoặc nhập nội dung để nghe thử.", "error");
      elements.text.focus();
      return;
    }
    const prepared = prepareSingleTtsInput(applyDictionary(text), Number(elements.rate.value));
    if (prepared.text.length > state.maxText) {
      setMessage(`Đoạn nghe thử tối đa ${state.maxText.toLocaleString("vi-VN")} ký tự.`, "error");
      return;
    }
    elements.previewSelection.disabled = true;
    setMessage("Đang render đoạn nghe thử…");
    try {
      const response = await fetch("/v1/tts", {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          text: prepared.text,
          rate: prepared.rate,
          filename: `${safeSlug(elements.projectName.value || "preview")}_preview.mp3`,
          ...selectedVoicePayload(),
        }),
      });
      if (!response.ok) throw new Error(await parseError(response));
      const blob = await response.blob();
      showAudio({
        blob,
        filename: contentDispositionFilename(response.headers.get("content-disposition")) || "preview.mp3",
        rate: prepared.rate,
        cache: response.headers.get("x-tts-cache"),
        cacheId: response.headers.get("x-tts-cache-id"),
        voiceName: decodeHeader(response.headers.get("x-tts-voice-name")) || state.voiceName,
        providerLabel: decodeHeader(response.headers.get("x-tts-provider-label")) || state.providerLabel,
      });
      elements.player.play().catch(() => undefined);
      setMessage(prepared.emotion ? `Đã render đoạn nghe thử với tag ${prepared.emotion.label}.` : "Đã render đoạn nghe thử.", "success");
    } catch (error) {
      setMessage(error.message || "Không thể nghe thử đoạn chọn.", "error");
    } finally {
      elements.previewSelection.disabled = false;
    }
  }

  function relativeTime(value) {
    const when = new Date(value).getTime();
    const diff = Math.max(0, Date.now() - when);
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return "vừa xong";
    if (minutes < 60) return `${minutes} phút trước`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} giờ trước`;
    return new Date(value).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  async function fetchCachedAudio(id, item = {}) {
    const response = await fetch(`/v1/cache/${encodeURIComponent(id)}`, { headers: authHeaders() });
    if (!response.ok) throw new Error(await parseError(response));
    const blob = await response.blob();
    showAudio({
      blob,
      filename: `co_gai_hoat_ngon_${id.slice(0, 12)}.${item.extension || "mp3"}`,
      rate: item.rate || 1,
      cache: "HIT",
      cacheId: id,
      voiceName: item.voice,
      providerLabel: item.provider_label,
    });
    elements.player.play().catch(() => undefined);
  }

  async function loadHistory() {
    try {
      const response = await fetch("/v1/history?limit=12", { headers: authHeaders(), cache: "no-store" });
      if (response.status === 401) {
        elements.historyList.innerHTML = "";
        elements.historyEmpty.textContent = "Nhập X-API-Key để xem thư viện cache local.";
        elements.historyEmpty.classList.remove("hidden");
        return;
      }
      if (!response.ok) throw new Error(await parseError(response));
      const items = await response.json();
      elements.historyList.innerHTML = "";
      elements.historyEmpty.classList.toggle("hidden", items.length > 0);
      for (const item of items) {
        const fragment = elements.historyTemplate.content.cloneNode(true);
        const row = fragment.querySelector(".history-item");
        fragment.querySelector(".history-preview").textContent = item.text_preview || "(Không có nội dung)";
        const providerLabel = item.provider_label || item.provider || "provider";
        fragment.querySelector(".history-meta").textContent = `${relativeTime(item.created_at)} · ${providerLabel} · ${item.char_count.toLocaleString("vi-VN")} ký tự · ${Number(item.rate).toFixed(2)}×`;
        fragment.querySelector(".history-play").addEventListener("click", async () => {
          try {
            setMessage("Đang tải audio từ cache local…");
            await fetchCachedAudio(item.id, item);
            setMessage("Đang phát audio từ cache local.", "success");
          } catch (error) { setMessage(error.message, "error"); }
        });
        fragment.querySelector(".history-download").addEventListener("click", async () => {
          try {
            await fetchCachedAudio(item.id, item);
            downloadCurrent();
          } catch (error) { setMessage(error.message, "error"); }
        });
        fragment.querySelector(".history-delete").addEventListener("click", async () => {
          if (!confirm("Xóa audio này khỏi cache local?")) return;
          try {
            const responseDelete = await fetch(`/v1/cache/${encodeURIComponent(item.id)}`, { method: "DELETE", headers: authHeaders() });
            if (!responseDelete.ok) throw new Error(await parseError(responseDelete));
            if (state.currentCacheId === item.id) {
              elements.player.pause();
              revokeCurrentUrl();
              state.currentBlob = null;
              state.currentCacheId = null;
              elements.player.removeAttribute("src");
              elements.player.load();
              elements.playerWrap.classList.add("hidden");
              elements.emptyPlayer.classList.remove("hidden");
            }
            setMessage("Đã xóa audio khỏi cache local.", "success");
            await loadHistory();
          } catch (error) { setMessage(error.message, "error"); }
        });
        elements.historyList.appendChild(fragment);
        row.dataset.cacheId = item.id;
      }
    } catch (error) {
      elements.historyList.innerHTML = "";
      elements.historyEmpty.textContent = error.message || "Không thể tải lịch sử audio.";
      elements.historyEmpty.classList.remove("hidden");
    }
  }

  async function clearCache() {
    if (!confirm("Xóa toàn bộ audio cache local?")) return;
    try {
      const response = await fetch("/v1/cache", { method: "DELETE", headers: authHeaders() });
      if (!response.ok) throw new Error(await parseError(response));
      const result = await response.json();
      if (state.currentCacheId) {
        elements.player.pause();
        revokeCurrentUrl();
        state.currentBlob = null;
        state.currentCacheId = null;
        elements.player.removeAttribute("src");
        elements.player.load();
        elements.playerWrap.classList.add("hidden");
        elements.emptyPlayer.classList.remove("hidden");
      }
      setMessage(`Đã clear cache (${result.deleted_files || 0} file).`, "success");
      await loadHistory();
    } catch (error) {
      setMessage(error.message || "Không thể clear cache.", "error");
    }
  }

  async function logout() {
    try {
      await fetch("/auth/logout", { method: "POST" });
    } finally {
      localStorage.removeItem("voxLocalApiKey");
      window.location.href = "/login";
    }
  }

  elements.text.addEventListener("input", () => {
    updateCount();
    updateQueueControls();
  });
  elements.rate.addEventListener("input", updateRate);
  elements.preset.addEventListener("change", applyPreset);
  elements.voiceSelect.addEventListener("change", () => {
    const voice = state.voices.find((item) => voiceKey(item) === elements.voiceSelect.value);
    applySelectedVoice(voice);
    if (state.queue.length) setMessage("Giọng mới sẽ áp dụng cho queue sau khi bấm Chia đoạn lại.");
  });
  elements.bgmVolume.value = localStorage.getItem("voxBgmVolume") || elements.bgmVolume.value;
  elements.subtitleMode.value = localStorage.getItem("voxSubtitleMode") || elements.subtitleMode.value;
  elements.subtitleDensity.value = localStorage.getItem("voxSubtitleDensity") || elements.subtitleDensity.value;
  elements.dictionary.value = localStorage.getItem("voxPronunciationDictionary") || "";
  elements.dictionary.addEventListener("change", () => {
    localStorage.setItem("voxPronunciationDictionary", elements.dictionary.value);
  });
  elements.projectName.value = localStorage.getItem("voxProjectName") || "";
  elements.projectName.addEventListener("change", () => {
    localStorage.setItem("voxProjectName", elements.projectName.value.trim());
  });
  elements.buildQueue.addEventListener("click", buildQueue);
  elements.generateQueue.addEventListener("click", generateQueueAll);
  elements.downloadMerged.addEventListener("click", downloadMergedQueue);
  elements.bgmVolume.addEventListener("input", () => {
    updateBgmVolume();
    localStorage.setItem("voxBgmVolume", elements.bgmVolume.value);
  });
  elements.subtitleMode.addEventListener("change", () => {
    localStorage.setItem("voxSubtitleMode", elements.subtitleMode.value);
  });
  elements.subtitleDensity.addEventListener("change", () => {
    localStorage.setItem("voxSubtitleDensity", elements.subtitleDensity.value);
  });
  elements.bgm.addEventListener("change", updateQueueControls);
  elements.exportSrt.addEventListener("click", exportSrt);
  elements.exportAss.addEventListener("click", exportAss);
  elements.exportTimeline.addEventListener("click", exportTimelineJson);
  elements.exportTikTokPack.addEventListener("click", exportTikTokPack);
  elements.downloadBgmMix.addEventListener("click", downloadBgmMix);
  elements.previewSelection.addEventListener("click", previewSelection);
  elements.clearQueue.addEventListener("click", clearQueue);
  elements.generate.addEventListener("click", generate);
  $("#clearBtn").addEventListener("click", () => { elements.text.value = ""; updateCount(); elements.text.focus(); });
  $("#refreshBtn").addEventListener("click", async () => { await ensureConfig(); await loadHistory(); });
  $("#loadHistoryBtn").addEventListener("click", loadHistory);
  elements.clearCache.addEventListener("click", clearCache);
  if (elements.logout) elements.logout.addEventListener("click", logout);
  elements.download.addEventListener("click", downloadCurrent);
  elements.copyLink.addEventListener("click", async () => {
    const url = state.currentCacheId ? `${location.origin}/v1/cache/${state.currentCacheId}` : location.origin;
    try { await navigator.clipboard.writeText(url); setMessage("Đã sao chép đường dẫn local. Nếu server bật key, người nhận vẫn cần X-API-Key.", "success"); }
    catch { setMessage("Trình duyệt không cho sao chép tự động.", "error"); }
  });
  elements.toggleKey.addEventListener("click", () => {
    elements.apiKey.type = elements.apiKey.type === "password" ? "text" : "password";
  });
  elements.apiKey.value = localStorage.getItem("voxLocalApiKey") || "";
  elements.apiKey.addEventListener("change", () => {
    localStorage.setItem("voxLocalApiKey", elements.apiKey.value.trim());
    loadHistory();
  });
  elements.apiKey.addEventListener("keydown", (event) => {
    if (event.key === "Enter") { event.preventDefault(); localStorage.setItem("voxLocalApiKey", elements.apiKey.value.trim()); loadHistory(); }
  });
  window.addEventListener("beforeunload", revokeCurrentUrl);

  updateRate();
  updateBgmVolume();
  updateCount();
  ensureConfig().then(loadVoices).then(loadHistory).then(updateQueueControls);
})();
