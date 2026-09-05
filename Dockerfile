FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        ffmpeg \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . ./

RUN mkdir -p /app/providers /app/audio_cache /app/logs /app/run \
    && if [ ! -d /app/providers/capcut-tts-api ]; then \
         git clone --depth 1 https://github.com/K07VN/capcut-tts-api.git /app/providers/capcut-tts-api; \
       fi \
    && python -m pip install requests

EXPOSE 8010

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8010"]
