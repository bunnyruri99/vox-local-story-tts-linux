"""Mock client used only to test this server without contacting any provider."""
from __future__ import annotations

import argparse
import base64
import io
import json
import math
import struct
import wave


def wav_data() -> bytes:
    sample_rate = 16000
    duration = 1.0
    frames = bytearray()
    for index in range(int(sample_rate * duration)):
        sample = int(11000 * math.sin(2 * math.pi * 440 * index / sample_rate))
        frames.extend(struct.pack("<h", sample))
    buff = io.BytesIO()
    with wave.open(buff, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(frames))
    return buff.getvalue()


parser = argparse.ArgumentParser()
parser.add_argument("mode")
parser.add_argument("--text")
parser.add_argument("--voice")
parser.add_argument("--resource-id")
parser.add_argument("--rate")
parser.add_argument("--task-id")
parser.add_argument("--token")
parser.add_argument("--device-json")
args = parser.parse_args()

if args.mode == "tts-new":
    print(json.dumps({"data": {"tasks": [{"id": "mock-task", "token": "mock-token", "status": "queueing"}]}}))
elif args.mode == "tts-query":
    encoded = base64.b64encode(wav_data()).decode("ascii")
    # The adapter does not download data URLs, so result is intentionally a test failure unless a local HTTP server is used.
    # This mock exists to validate tts-new parsing only.
    print(json.dumps({"data": {"tasks": [{"id": "mock-task", "token": "mock-token", "status": "success", "payload": json.dumps({"audio_url": "http://127.0.0.1:9999/mock.wav"})}]}}))
else:
    raise SystemExit("unsupported mock mode")
