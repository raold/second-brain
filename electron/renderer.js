// Theme toggle logic
const themeToggle = document.getElementById('themeToggle');
const themeNames = ['Gruvbox Light', 'Gruvbox Dark', 'Dracula'];
const themeKeys = ['light', 'dark', 'dracula'];
function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
  themeToggle.textContent = `🌗 ${themeNames[themeKeys.indexOf(theme)]}`;
}
function getTheme() {
  return localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
}
setTheme(getTheme());
themeToggle.onclick = () => {
  const idx = themeKeys.indexOf(getTheme());
  const next = themeKeys[(idx + 1) % themeKeys.length];
  setTheme(next);
};

// Mic recording logic
let mediaRecorder, audioChunks = [], isRecording = false;
const recBtn = document.getElementById('recBtn');
const statusDiv = document.getElementById('status');
const transcriptDiv = document.getElementById('transcript');
const subtitlesDiv = document.getElementById('subtitles');
const audioControls = document.getElementById('audioControls');
let ws, tokenBuffer = [], ttsBuffer = '', ttsTimeout;

recBtn.onclick = async () => {
  if (!isRecording) {
    audioChunks = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
      mediaRecorder.onstop = onRecordingStop;
      mediaRecorder.start();
      isRecording = true;
      recBtn.textContent = '⏹️ Stop';
      recBtn.classList.add('recording');
      statusDiv.textContent = 'Recording...';
      transcriptDiv.textContent = '';
      subtitlesDiv.textContent = '';
      audioControls.innerHTML = '';
    } catch (e) {
      statusDiv.textContent = 'Mic access denied.';
    }
  } else {
    mediaRecorder.stop();
    isRecording = false;
    recBtn.textContent = '🎤 Record';
    recBtn.classList.remove('recording');
    statusDiv.textContent = 'Processing...';
  }
};

async function onRecordingStop() {
  const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
  // Show playback
  const url = URL.createObjectURL(audioBlob);
  audioControls.innerHTML = `<audio controls src="${url}" style="width:100%"></audio>`;
  // Send to /transcribe
  statusDiv.textContent = 'Transcribing...';
  const formData = new FormData();
  formData.append('file', audioBlob, 'audio.webm');
  try {
    const res = await fetch('http://localhost:8000/transcribe', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + (localStorage.getItem('token') || '') },
      body: formData
    });
    if (!res.ok) throw new Error('Transcription failed');
    const data = await res.json();
    transcriptDiv.textContent = data.transcript;
    statusDiv.textContent = 'Transcript ready. Connecting to LLM...';
    // Connect to /ws/generate and stream tokens
    connectToWSGenerate(data.transcript);
  } catch (e) {
    statusDiv.textContent = 'Transcription error.';
  }
}

const ELEVENLABS_API_KEY = 'YOUR_ELEVENLABS_API_KEY'; // Set your key here
const ELEVENLABS_VOICE_ID = 'EXAVITQu4vr4xnSDxMaL'; // Default voice
const TTS_CHUNK_SIZE = 30; // tokens
const TTS_PAUSE_MS = 1200;

let audioQueue = [], currentAudioIdx = -1;

async function streamToTTS(text, chunkIdx) {
  if (!text.trim()) return;
  setTTSStatus(chunkIdx, 'processing');
  try {
    const resp = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${getVoiceId()}/stream`, {
      method: 'POST',
      headers: {
        'xi-api-key': getApiKey(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text, voice_settings: { stability: 0.5, similarity_boost: 0.5 } })
    });
    if (!resp.ok) throw new Error('TTS failed');
    const reader = resp.body.getReader();
    let audioChunks = [];
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      audioChunks.push(value);
    }
    const audioBlob = new Blob(audioChunks, { type: 'audio/mpeg' });
    const url = URL.createObjectURL(audioBlob);
    audioQueue.push({ url, text, idx: chunkIdx });
    renderAudioQueue();
    setTTSStatus(chunkIdx, 'ready');
    if (audioQueue.length === 1 || currentAudioIdx === chunkIdx - 1) {
      playAudioChunk(chunkIdx);
    }
  } catch (e) {
    setTTSStatus(chunkIdx, 'error');
    statusDiv.textContent = 'TTS error.';
  }
}

function setTTSStatus(idx, status) {
  const el = document.getElementById('tts-status-' + idx);
  if (el) {
    el.textContent = status === 'processing' ? '🔄 Processing...' : status === 'ready' ? '▶️ Ready' : status === 'error' ? '❌ Error' : '';
    el.setAttribute('aria-label', status);
  }
}

function renderAudioQueue() {
  audioControls.innerHTML = '';
  audioQueue.forEach((chunk, i) => {
    const isPlaying = i === currentAudioIdx;
    const btn = `<button aria-label="Play chunk ${i+1}" tabindex="0" onclick="window.playAudioChunk(${i})">${isPlaying ? '⏸️' : '▶️'}</button>`;
    const dl = `<a href="${chunk.url}" download="tts-chunk-${i+1}.mp3" aria-label="Download chunk ${i+1}">💾</a>`;
    audioControls.innerHTML += `<div style="margin-bottom:0.5em;display:flex;align-items:center;gap:0.5em;"><span id="tts-status-${chunk.idx}">${i === currentAudioIdx ? '▶️ Playing' : '▶️ Ready'}</span> ${btn} ${dl} <span style="flex:1;color:var(--fg-alt);font-size:0.95em;">${chunk.text.replace(/</g,'&lt;')}</span></div>`;
  });
  updateDownloadButton();
}

window.playAudioChunk = function(idx) {
  if (audioQueue[idx]) {
    const audio = new Audio(audioQueue[idx].url);
    currentAudioIdx = idx;
    renderAudioQueue();
    highlightSubtitleChunk(idx);
    audio.onended = () => {
      if (audioQueue[idx+1]) {
        playAudioChunk(idx+1);
      } else {
        currentAudioIdx = -1;
        renderAudioQueue();
        highlightSubtitleChunk(-1);
      }
    };
    audio.play();
  }
};

function highlightSubtitleChunk(idx) {
  // For now, just bold the chunk text in the subtitles area
  let html = '';
  let offset = 0;
  audioQueue.forEach((chunk, i) => {
    const safe = chunk.text.replace(/</g,'&lt;');
    if (i === idx) {
      html += `<b style="background:var(--accent);color:var(--bg);padding:0.1em 0.2em;border-radius:3px;">${safe}</b>`;
    } else {
      html += safe;
    }
    offset += chunk.text.length;
  });
  subtitlesDiv.innerHTML = html;
}

function triggerTTSBuffer() {
  if (!ttsBuffer.trim()) return;
  const text = ttsBuffer;
  ttsBuffer = '';
  streamToTTS(text, audioQueue.length);
}

function connectToWSGenerate(prompt) {
  subtitlesDiv.textContent = '';
  tokenBuffer = [];
  ttsBuffer = '';
  if (ws) ws.close();
  ws = new WebSocket('ws://localhost:8000/ws/generate?token=' + (localStorage.getItem('token') || ''));
  ws.onopen = () => {
    ws.send(JSON.stringify({ prompt, json: true }));
    statusDiv.textContent = 'Connected to LLM. Streaming...';
  };
  ws.onmessage = (event) => {
    let msg;
    try { msg = JSON.parse(event.data); } catch { return; }
    if (msg.error) {
      statusDiv.textContent = 'LLM error: ' + msg.error;
      return;
    }
    if (msg.text || msg.chunk) {
      const token = msg.text || msg.chunk;
      tokenBuffer.push(token);
      ttsBuffer += token;
      subtitlesDiv.textContent += token;
      subtitlesDiv.scrollTop = subtitlesDiv.scrollHeight;
      // TTS batching logic
      if (tokenBuffer.length % getChunkSize() === 0) {
        triggerTTSBuffer();
      } else {
        if (ttsTimeout) clearTimeout(ttsTimeout);
        ttsTimeout = setTimeout(triggerTTSBuffer, getPauseMs());
      }
    }
  };
  ws.onerror = (e) => {
    statusDiv.textContent = 'WebSocket error.';
  };
  ws.onclose = () => {
    statusDiv.textContent = 'LLM connection closed.';
    // Flush any remaining buffer
    if (ttsBuffer.trim()) triggerTTSBuffer();
  };
}

// Settings panel logic
const settingsBtn = document.getElementById('settingsBtn');
const settingsPanel = document.getElementById('settingsPanel');
const closeSettings = document.getElementById('closeSettings');
const saveSettings = document.getElementById('saveSettings');
const apiKeyInput = document.getElementById('apiKeyInput');
const voiceSelect = document.getElementById('voiceSelect');
const chunkSizeInput = document.getElementById('chunkSizeInput');
const pauseInput = document.getElementById('pauseInput');
const downloadFullAudio = document.getElementById('downloadFullAudio');

let userSettings = {
  apiKey: '',
  voice: ELEVENLABS_VOICE_ID,
  chunkSize: TTS_CHUNK_SIZE,
  pause: TTS_PAUSE_MS,
  theme: getTheme(),
};

function loadSettings() {
  const s = JSON.parse(localStorage.getItem('voiceAppSettings') || '{}');
  userSettings = { ...userSettings, ...s };
  apiKeyInput.value = userSettings.apiKey || '';
  chunkSizeInput.value = userSettings.chunkSize;
  pauseInput.value = userSettings.pause;
  setTheme(userSettings.theme);
}
function saveSettingsToStorage() {
  userSettings.apiKey = apiKeyInput.value;
  userSettings.voice = voiceSelect.value;
  userSettings.chunkSize = parseInt(chunkSizeInput.value) || 30;
  userSettings.pause = parseInt(pauseInput.value) || 1200;
  userSettings.theme = getTheme();
  localStorage.setItem('voiceAppSettings', JSON.stringify(userSettings));
}
settingsBtn.onclick = async () => {
  loadSettings();
  await populateVoices();
  settingsPanel.style.display = 'flex';
  voiceSelect.value = userSettings.voice;
};
closeSettings.onclick = () => { settingsPanel.style.display = 'none'; };
saveSettings.onclick = () => {
  saveSettingsToStorage();
  settingsPanel.style.display = 'none';
  // Update TTS params
  ELEVENLABS_VOICE_ID = userSettings.voice;
  TTS_CHUNK_SIZE = userSettings.chunkSize;
  TTS_PAUSE_MS = userSettings.pause;
};

async function populateVoices() {
  voiceSelect.innerHTML = '<option>Loading...</option>';
  try {
    const res = await fetch('https://api.elevenlabs.io/v1/voices', {
      headers: { 'xi-api-key': getApiKey() }
    });
    const data = await res.json();
    voiceSelect.innerHTML = '';
    data.voices.forEach(v => {
      const opt = document.createElement('option');
      opt.value = v.voice_id;
      opt.textContent = v.name + (v.labels && v.labels.language ? ` (${v.labels.language})` : '');
      voiceSelect.appendChild(opt);
    });
  } catch {
    voiceSelect.innerHTML = '<option value="EXAVITQu4vr4xnSDxMaL">Default (Rachel)</option>';
  }
}

// Use userSettings for TTS
function getApiKey() { return apiKeyInput.value || userSettings.apiKey || ELEVENLABS_API_KEY; }
function getVoiceId() { return voiceSelect.value || userSettings.voice || ELEVENLABS_VOICE_ID; }
function getChunkSize() { return parseInt(chunkSizeInput.value) || userSettings.chunkSize || 30; }
function getPauseMs() { return parseInt(pauseInput.value) || userSettings.pause || 1200; }

// Download full audio logic
function concatAudioBlobs(blobs, cb) {
  // Simple concat for MP3 (may have small gaps, but works for demo)
  const reader = new FileReader();
  let parts = [];
  let i = 0;
  function readNext() {
    if (i >= blobs.length) {
      cb(new Blob(parts, { type: 'audio/mpeg' }));
      return;
    }
    reader.onload = function(e) {
      parts.push(new Uint8Array(e.target.result));
      i++;
      readNext();
    };
    reader.readAsArrayBuffer(blobs[i]);
  }
  readNext();
}
downloadFullAudio.onclick = () => {
  const blobs = audioQueue.map(a => fetch(a.url).then(r => r.blob()));
  Promise.all(blobs).then(blobArr => {
    concatAudioBlobs(blobArr, (fullBlob) => {
      const url = URL.createObjectURL(fullBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'full-tts.mp3';
      a.click();
    });
  });
};
// Show/hide download button
function updateDownloadButton() {
  downloadFullAudio.style.display = audioQueue.length > 0 ? '' : 'none';
} 