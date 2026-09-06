---
title: Aris Kokoro TTS Service
colorFrom: green
colorTo: blue
sdk: docker
app_port: 8080
app_file: Dockerfile
pinned: false
---

# Aris Kokoro TTS Service

A Hugging Face Docker Space that exposes Kokoro-82M text-to-speech for Aris.
The API is compatible with the Google Cloud Text-to-Speech request and response
shape used by the Aris backend.

## API

`POST /v1/text:synthesize`

```json
{
  "input": { "text": "Hello from Aris." },
  "voice": { "name": "af_heart" },
  "audioConfig": { "audioEncoding": "MP3", "speakingRate": 1.0 }
}
```

The response is:

```json
{ "audioContent": "<base64 audio>" }
```

Supported encodings are `LINEAR16` (WAV), `MP3`, and `OGG_OPUS`. `audioContent`
is base64 encoded and can be passed directly to the existing Aris voice flow.

## Configuration

- `KOKORO_VOICE` - default Kokoro voice, defaults to `af_heart`
- `KOKORO_LANG_CODE` - Kokoro pipeline language, defaults to `a` (American English)
- `KOKORO_MAX_CHARS` - maximum text length, defaults to `12000`
- `PORT` - listen port, defaults to `8080`

Kokoro-82M is downloaded from Hugging Face on the first synthesis request and
cached in the Space container cache. A Space with at least 2 GB RAM is
recommended; CPU inference works but GPU hardware is faster.

## Connect Aris

Set the Aris server's TTS URL to the Space endpoint:

```env
VOICE_TTS_URL=https://<your-tts-space>.hf.space/v1/text:synthesize
VOICE_TTS_VOICE=af_heart
```

Keep `VOICE_API_KEY` configured if Aris still uses Google Speech-to-Text. The
TTS service does not require an API key by default; put it behind an authenticated
proxy or add platform authentication if the Space is private.

## GitHub Actions deployment

The workflow deploys `main` to a Docker-enabled Hugging Face Space. Add these
repository secrets in GitHub:

- `HF_TOKEN` - a Hugging Face token with write access to the Space
- `HF_SPACE_REPO` - the Space identifier in `owner/space-name` form, for example
  `Knowledge-Benjamin/aris-kokoro-tts`

Do not set `HF_SPACE_REPO` to a GitHub repository URL, an `hf.space` URL, or the
full Hugging Face URL. The target Space must already exist at
`https://huggingface.co/spaces/<owner>/<space-name>`.
