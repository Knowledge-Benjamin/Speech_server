import base64
import io
import os
import subprocess
import tempfile
from functools import lru_cache
from typing import Any

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


class SynthesisInput(BaseModel):
    text: str = Field(min_length=1)


class VoiceConfig(BaseModel):
    name: str | None = None


class AudioConfig(BaseModel):
    audioEncoding: str = "MP3"
    speakingRate: float = Field(default=1.0, gt=0.5, le=2.0)


class SynthesisRequest(BaseModel):
    input: SynthesisInput
    voice: VoiceConfig | None = None
    audioConfig: AudioConfig | None = None


app = FastAPI(title="Aris Kokoro TTS", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_pipeline():
    from kokoro import KPipeline

    return KPipeline(lang_code=os.getenv("KOKORO_LANG_CODE", "a"))


def render_audio(text: str, voice: str, speed: float) -> tuple[np.ndarray, int]:
    pipeline = get_pipeline()
    chunks: list[np.ndarray] = []
    for _, _, audio in pipeline(text, voice=voice, speed=speed, split_pattern=r"\n+"):
        if audio is not None:
            chunks.append(np.asarray(audio, dtype=np.float32))

    if not chunks:
        raise HTTPException(status_code=422, detail="Kokoro produced no audio")
    return np.concatenate(chunks), 24000


def encode_audio(audio: np.ndarray, sample_rate: int, encoding: str) -> bytes:
    normalized = encoding.upper()
    if normalized == "LINEAR16":
        output = io.BytesIO()
        sf.write(output, audio, sample_rate, format="WAV", subtype="PCM_16")
        return output.getvalue()

    format_name = "mp3" if normalized == "MP3" else "ogg"
    codec = "libmp3lame" if normalized == "MP3" else "libopus"
    with tempfile.TemporaryDirectory() as directory:
        wav_path = os.path.join(directory, "input.wav")
        output_path = os.path.join(directory, f"output.{format_name}")
        sf.write(wav_path, audio, sample_rate, format="WAV", subtype="PCM_16")
        result = subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-y", "-i", wav_path, "-c:a", codec, output_path],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail="Audio encoding failed")
        with open(output_path, "rb") as encoded:
            return encoded.read()


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "aris-kokoro-tts"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aris-kokoro-tts"}


@app.post("/v1/text:synthesize")
def synthesize(request: SynthesisRequest) -> dict[str, Any]:
    text = request.input.text.strip()
    max_chars = int(os.getenv("KOKORO_MAX_CHARS", "12000"))
    if not text:
        raise HTTPException(status_code=400, detail="input.text is required")
    if len(text) > max_chars:
        raise HTTPException(status_code=413, detail=f"input.text exceeds {max_chars} characters")

    audio_config = request.audioConfig or AudioConfig()
    encoding = audio_config.audioEncoding.upper()
    if encoding not in {"LINEAR16", "MP3", "OGG_OPUS"}:
        raise HTTPException(status_code=400, detail="audioEncoding must be LINEAR16, MP3, or OGG_OPUS")

    voice = (request.voice.name if request.voice else None) or os.getenv("KOKORO_VOICE", "af_heart")
    try:
        audio, sample_rate = render_audio(text, voice, audio_config.speakingRate)
        encoded = encode_audio(audio, sample_rate, encoding)
    except HTTPException:
        raise
    except Exception as error:
        print(f"Kokoro synthesis failed: {error}", flush=True)
        raise HTTPException(status_code=500, detail="Speech synthesis failed") from error

    return {"audioContent": base64.b64encode(encoded).decode("ascii")}
