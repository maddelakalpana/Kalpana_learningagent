"""TTS Service using Deepgram Aura."""
import os
import base64
import httpx
from dotenv import load_dotenv
from backend.config import settings

load_dotenv()


async def generate_tts(text: str) -> str:
    """Generate audio using Deepgram Aura TTS API and return base64-encoded audio."""
    api_key = settings.deepgram_api_key or os.getenv("DEEPGRAM_API_KEY", "")
    if not api_key:
        print("[TTS] Error: DEEPGRAM_API_KEY is missing in .env", flush=True)
        raise ValueError("DEEPGRAM_API_KEY is missing")

    model = getattr(settings, "deepgram_tts_model", "") or os.getenv("DEEPGRAM_TTS_MODEL", "aura-asteria-en")
    url = f"https://api.deepgram.com/v1/speak?model={model}"

    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"text": text}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            err_msg = f"Deepgram TTS failed with status {response.status_code}: {response.text}"
            print(f"[TTS] {err_msg}", flush=True)
            raise RuntimeError(err_msg)

        audio_bytes = response.content
        return base64.b64encode(audio_bytes).decode("utf-8")
