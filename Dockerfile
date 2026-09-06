FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/data/huggingface \
    KOKORO_VOICE=af_heart \
    KOKORO_LANG_CODE=a \
    KOKORO_MAX_CHARS=12000 \
    PORT=8080

RUN apt-get update \
  && apt-get install -y --no-install-recommends espeak-ng ffmpeg libsndfile1 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py README.md ./
RUN mkdir -p /data/huggingface

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
