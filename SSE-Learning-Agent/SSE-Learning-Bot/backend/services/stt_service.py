"""STT Service using Deepgram Nova."""
import os
import httpx
from dotenv import load_dotenv
from backend.config import settings

load_dotenv()


async def transcribe_audio(audio_data: bytes, mimetype: str = "audio/webm") -> str:
    """Transcribe an audio buffer using Deepgram API."""
    api_key = settings.deepgram_api_key or os.getenv("DEEPGRAM_API_KEY", "")
    if not api_key:
        print("[STT] Error: DEEPGRAM_API_KEY is missing in .env", flush=True)
        return ""

    model = getattr(settings, "deepgram_stt_model", "") or os.getenv("DEEPGRAM_STT_MODEL", "nova-3")
    url = f"https://api.deepgram.com/v1/listen?model={model}&smart_format=true&punctuate=true"

    clean_mime = mimetype.split(";")[0].strip() if mimetype else "audio/webm"
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": clean_mime,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, headers=headers, content=audio_data)
            if response.status_code != 200:
                print(f"[STT] Deepgram STT failed ({response.status_code}): {response.text}", flush=True)
                return ""

            result = response.json()
            channels = result.get("results", {}).get("channels", [])
            if not channels:
                return ""
            alternatives = channels[0].get("alternatives", [])
            if not alternatives:
                return ""
            transcript = alternatives[0].get("transcript", "").strip()
            return transcript
    except Exception as e:
        print(f"[STT] Deepgram transcription error: {e}", flush=True)
        return ""
