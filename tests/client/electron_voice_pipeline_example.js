// Electron Renderer: Voice Assistant Pipeline Example
// 1. Mic recording → 2. /transcribe → 3. /ws/generate → 4. ElevenLabs TTS → 5. Audio playback

const API_TOKEN = '<API_TOKEN>'; // Set your API token here
const ELEVENLABS_API_KEY = '<ELEVENLABS_API_KEY>'; // Set your ElevenLabs API key here
const TTS_VOICE_ID = 'EXAVITQu4vr4xnSDxMaL';
const BATCH_SIZE = 5;

let audioChunks = [];
let mediaRecorder = null;

// 1. Start mic recording
async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  audioChunks = [];
  mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
  mediaRecorder.start();
  console.log('Recording started...');
}

// 2. Stop recording and transcribe
async function stopAndTranscribe() {
  return new Promise((resolve, reject) => {
    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
      try {
        const transcript = await transcribeAudio(audioBlob);
        resolve(transcript);
      } catch (err) {
        reject(err);
      }
    };
    mediaRecorder.stop();
    console.log('Recording stopped. Transcribing...');
  });
}

// 3. Upload audio to /transcribe
async function transcribeAudio(audioBlob) {
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.webm');
  const resp = await fetch('http://localhost:8000/transcribe', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${API_TOKEN}` },
    body: formData
  });
  if (!resp.ok) throw new Error('Transcription failed');
  const data = await resp.json();
  console.log('Transcript:', data.transcript);
  return data.transcript;
}

// 4. Stream LLM output via WebSocket
function streamLLM(prompt, onToken, onEnd) {
  const ws = new WebSocket(`ws://localhost:8000/ws/generate?token=${API_TOKEN}`);
  ws.onopen = () => ws.send(JSON.stringify({ prompt, json: true }));
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.text) onToken(data.text);
    if (data.end) { ws.close(); if (onEnd) onEnd(); }
  };
  ws.onerror = (e) => console.error('WebSocket error:', e);
}

// 5. ElevenLabs TTS API call
async function elevenLabsTTS(text, apiKey, voiceId = TTS_VOICE_ID) {
  const resp = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
    method: 'POST',
    headers: {
      'xi-api-key': apiKey,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ text, voice_settings: { stability: 0.5, similarity_boost: 0.5 } })
  });
  if (!resp.ok) throw new Error('TTS failed');
  return await resp.arrayBuffer(); // MP3 audio
}

// 6. Audio playback
function playAudioBuffer(arrayBuffer) {
  const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  audioCtx.decodeAudioData(arrayBuffer, (buffer) => {
    const source = audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(audioCtx.destination);
    source.start(0);
  });
}

// 7. Full pipeline automation
async function runVoicePipeline() {
  try {
    await startRecording();
    // Wait for user to stop recording (e.g., via UI button)
    // ...
    // For demo: setTimeout(() => mediaRecorder.stop(), 5000);
    // After stop, get transcript
    const transcript = await stopAndTranscribe();
    // Stream LLM output, batch tokens, send to TTS
    let tokens = [];
    let batchNum = 1;
    streamLLM(transcript, async (token) => {
      tokens.push(token);
      if (tokens.length >= BATCH_SIZE) {
        const batch = tokens.join(' ');
        console.log(`[Batch ${batchNum}] Sending to TTS:`, batch);
        const audio = await elevenLabsTTS(batch, ELEVENLABS_API_KEY);
        playAudioBuffer(audio);
        tokens = [];
        batchNum++;
      }
    }, async () => {
      // On end, send any remaining tokens
      if (tokens.length) {
        const batch = tokens.join(' ');
        console.log(`[Batch ${batchNum}] Sending to TTS:`, batch);
        const audio = await elevenLabsTTS(batch, ELEVENLABS_API_KEY);
        playAudioBuffer(audio);
      }
      console.log('Pipeline complete.');
    });
  } catch (err) {
    console.error('Pipeline error:', err);
  }
}

// Expose functions for UI buttons
window.voicePipeline = {
  startRecording,
  stopAndTranscribe,
  runVoicePipeline
}; 