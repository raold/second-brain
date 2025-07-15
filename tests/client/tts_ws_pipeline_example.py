import asyncio
import websockets
import json
import requests
import argparse
import os
import tempfile
import sys

API_URL = "ws://localhost:8000/ws/generate?token=test-token"
TTS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # ElevenLabs default voice
BATCH_SIZE = 5  # Number of tokens per TTS batch

# Play audio (cross-platform)
def play_audio(audio_bytes):
    try:
        import simpleaudio as sa
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            f.write(audio_bytes)
            f.flush()
            wave_obj = sa.WaveObject.from_wave_file(f.name)
            play_obj = wave_obj.play()
            play_obj.wait_done()
    except ImportError:
        print("[WARN] Install simpleaudio for audio playback, or play the file manually.")

# ElevenLabs TTS API call
def elevenlabs_tts(text, api_key, voice_id=DEFAULT_VOICE_ID, language=None):
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
    }
    if language:
        payload["model_id"] = language
    url = TTS_API_URL.format(voice_id=voice_id)
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code == 200:
        return resp.content
    else:
        print(f"[TTS ERROR] {resp.status_code}: {resp.text}")
        return None

async def tts_pipeline(prompt, api_key, language=None, voice_id=DEFAULT_VOICE_ID):
    print("Connecting to LLM WebSocket...")
    async with websockets.connect(API_URL) as ws:
        # Send prompt
        await ws.send(json.dumps({"prompt": prompt, "json": True}))
        print(f"Sent prompt: {prompt}")
        tokens = []
        batch_num = 1
        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)
                if "text" in data:
                    token = data["text"]
                    print(f"Received token: {token}")
                    tokens.append(token)
                    # Batch tokens for TTS
                    if len(tokens) >= BATCH_SIZE:
                        batch = " ".join(tokens)
                        print(f"[Batch {batch_num}] Sending to TTS: {batch}")
                        audio = elevenlabs_tts(batch, api_key, voice_id, language)
                        if audio:
                            print(f"[Batch {batch_num}] Playing audio...")
                            play_audio(audio)
                        tokens = []
                        batch_num += 1
                if data.get("end"):
                    print("LLM stream ended.")
                    break
            except websockets.ConnectionClosed:
                print("WebSocket closed.")
                break
        # Final batch
        if tokens:
            batch = " ".join(tokens)
            print(f"[Batch {batch_num}] Sending to TTS: {batch}")
            audio = elevenlabs_tts(batch, api_key, voice_id, language)
            if audio:
                print(f"[Batch {batch_num}] Playing audio...")
                play_audio(audio)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM WebSocket to ElevenLabs TTS pipeline client.")
    parser.add_argument("--prompt", type=str, default="Summarize the latest news about AI.", help="Prompt to send to LLM.")
    parser.add_argument("--api-key", type=str, default=os.getenv("ELEVENLABS_API_KEY"), help="ElevenLabs API key.")
    parser.add_argument("--language", type=str, default=None, help="Language/model for TTS (optional)")
    parser.add_argument("--voice-id", type=str, default=DEFAULT_VOICE_ID, help="ElevenLabs voice ID")
    args = parser.parse_args()
    if not args.api_key:
        print("[ERROR] Please provide --api-key or set ELEVENLABS_API_KEY env var.")
        sys.exit(1)
    asyncio.run(tts_pipeline(args.prompt, args.api_key, args.language, args.voice_id)) 