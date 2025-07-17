import argparse
import os

import requests

API_URL = "http://localhost:8000/transcribe"
TOKEN = os.getenv("API_TOKEN", "test-token")

parser = argparse.ArgumentParser(description="Test /transcribe endpoint with an audio file.")
parser.add_argument("audio_file", type=str, help="Path to audio file (wav, mp3, m4a, etc)")
parser.add_argument("--token", type=str, default=TOKEN, help="API token (default: test-token or $API_TOKEN)")
parser.add_argument("--language", type=str, default=None, help="Language code for transcription (optional)")
args = parser.parse_args()

headers = {"Authorization": f"Bearer {args.token}"}
files = {"file": open(args.audio_file, "rb")}
data = {}
if args.language:
    data["language"] = args.language

print(f"Uploading {args.audio_file} to /transcribe...")
resp = requests.post(API_URL, headers=headers, files=files, data=data)

if resp.status_code == 200:
    print("Transcript:")
    print(resp.json()["transcript"])
else:
    print(f"[ERROR] {resp.status_code}: {resp.text}") 