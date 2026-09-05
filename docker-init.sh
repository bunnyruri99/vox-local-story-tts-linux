#!/bin/sh
set -eu

if [ ! -f .env ]; then
  cp .env.example .env
  sed -i 's/^HOST=.*/HOST=0.0.0.0/' .env
  sed -i 's/^PORT=.*/PORT=8010/' .env
  echo "Created .env from .env.example"
fi

mkdir -p audio_cache logs

echo "Building image..."
docker compose build

echo "Starting Vox TTS..."
docker compose up -d

echo "Waiting for service..."
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8010/health >/dev/null 2>&1; then
    echo "Vox TTS is ready: http://127.0.0.1:8010"
    exit 0
  fi
  sleep 2
done

echo "Service did not become healthy. Recent logs:"
docker compose logs --tail=100 vox-tts
exit 1
