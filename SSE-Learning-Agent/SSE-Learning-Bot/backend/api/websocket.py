"""WebSocket handler for AI Learning Assistant sessions."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.stt_service import transcribe_audio
from backend.services.tts_service import generate_tts
from backend.services.llm_service import (
    generate_teach_response, generate_doubt_response,
    stream_teach_response, stream_doubt_response,
)
from backend.api.routes import sessions, _save_sessions, _load_sessions
import json
import base64
import re
import traceback
from datetime import datetime

router = APIRouter()


def _get_session_or_close(session_id: str) -> dict | None:
    global sessions
    if session_id not in sessions:
        sessions.update(_load_sessions())
    return sessions.get(session_id)



def parse_mcq_from_text(raw_text: str):
    """Extract [MCQ]...[/MCQ] block if present, returning (clean_text, mcq_dict_or_None)."""
    pattern = r"\[MCQ\]([\s\S]*?)(?:\[/MCQ\]|$)"
    match = re.search(pattern, raw_text)
    if not match:
        return raw_text.strip(), None

    clean_text = re.sub(pattern, "", raw_text).strip()
    mcq_raw = match.group(1).strip()

    json_match = re.search(r"(\{[\s\S]*\})", mcq_raw)
    if json_match:
        mcq_raw = json_match.group(1).strip()

    try:
        mcq_data = json.loads(mcq_raw)
        if isinstance(mcq_data, dict) and "question" in mcq_data and "options" in mcq_data:
            return clean_text, mcq_data
    except Exception as e:
        print(f"[MCQ Parse Error] {e}", flush=True)

    return clean_text, None


def parse_speech_notes_mcq(raw_text: str):
    """
    Extract:
    1. speech_text: What avatar speaks (spoken dialogue, TTS, and avatar subtitle box).
    2. notes_text: What appears in the chat box transcript (structured concept notes, key takeaways).
    3. mcq_data: Interactive check question (if any).
    """
    clean_text, mcq_data = parse_mcq_from_text(raw_text)

    # Check for [SPEECH]...[/SPEECH] and [NOTES]...[/NOTES]
    speech_match = re.search(r"\[SPEECH\]([\s\S]*?)(?:\[/SPEECH\]|$)", clean_text, re.IGNORECASE)
    notes_match = re.search(r"\[NOTES\]([\s\S]*?)(?:\[/NOTES\]|$)", clean_text, re.IGNORECASE)

    if speech_match and notes_match:
        speech = speech_match.group(1).strip()
        notes = notes_match.group(1).strip()
    elif speech_match:
        speech = speech_match.group(1).strip()
        notes = re.sub(r"\[SPEECH\][\s\S]*?(?:\[/SPEECH\]|$)", "", clean_text, flags=re.IGNORECASE).strip()
        notes = re.sub(r"\[/?NOTES\]", "", notes).strip()
    elif notes_match:
        notes = notes_match.group(1).strip()
        speech = re.sub(r"\[NOTES\][\s\S]*?(?:\[/NOTES\]|$)", "", clean_text, flags=re.IGNORECASE).strip()
    else:
        # Fallback if tags omitted by LLM:
        # Check if text has bullet points (• or * or -)
        parts = re.split(r"(?:^|\n)\s*[•\*\-]\s+", clean_text, maxsplit=1)
        if len(parts) > 1 and parts[0].strip():
            speech = parts[0].strip()
            notes = "• " + parts[1].strip()
        else:
            speech = clean_text
            notes = clean_text

    # Clean any stray tags
    speech = re.sub(r"\[/?(SPEECH|NOTES)\]", "", speech, flags=re.IGNORECASE).strip()
    notes = re.sub(r"\[/?(SPEECH|NOTES)\]", "", notes, flags=re.IGNORECASE).strip()

    return speech, notes, mcq_data


def clean_text_for_tts(text: str) -> str:
    """Strip all markdown asterisks, bold/italic symbols, and bullet markers so Deepgram TTS speaks clean natural voice."""
    if not text:
        return ""
    cleaned = re.sub(r"[\*_]{1,3}(.*?)[*_]{1,3}", r"\1", text)
    cleaned = re.sub(r"^[#\-\*\>\•\s]+", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.replace("*", "").replace("_", "").replace("#", "").replace("`", "")
    return re.sub(r"\s+", " ", cleaned).strip()


async def _speak(websocket: WebSocket, raw_text: str) -> None:
    """Parse text into spoken dialogue and written study notes, sending to frontend."""
    speech, notes, mcq_data = parse_speech_notes_mcq(raw_text)

    payload = {
        "type": "ai_response_done",
        "speech": speech,
        "notes": notes,
    }
    if mcq_data:
        payload["mcq"] = mcq_data

    await websocket.send_json(payload)

    try:
        spoken_dialogue = clean_text_for_tts(speech)
        if len(spoken_dialogue) > 900:
            spoken_dialogue = spoken_dialogue[:900].rsplit(" ", 1)[0] + "."
        if mcq_data and "question" in mcq_data:
            spoken_dialogue += " I've also placed a quick interactive check question on your screen to test this concept."

        audio_b64 = await generate_tts(spoken_dialogue)
        await websocket.send_json({"type": "ai_audio", "data": audio_b64, "text": speech})
    except Exception as tts_err:
        print(f"[TTS] Error: {tts_err}", flush=True)
        traceback.print_exc()
        await websocket.send_json({
            "type": "server_status",
            "message": "Voice playback unavailable — reading the text above instead.",
        })


async def _stream_and_speak(websocket: WebSocket, stream_generator, mode: str) -> str:
    """Stream LLM response chunk-by-chunk over WebSocket, separating speech subtitles and chat notes."""
    full_text = ""

    try:
        async for chunk in stream_generator:
            full_text += chunk
            partial_speech, partial_notes, _ = parse_speech_notes_mcq(full_text)
            await websocket.send_json({
                "type": "ai_stream_chunk",
                "speech_chunk": partial_speech,
                "notes_chunk": partial_notes,
                "accumulated": full_text,
            })
    except Exception as e:
        print(f"[Stream] Error during streaming: {e}", flush=True)
        traceback.print_exc()
        if not full_text:
            raise

    # Parse distinct speech, notes, and MCQ
    speech, notes, mcq_data = parse_speech_notes_mcq(full_text)

    # Send final complete response
    done_payload = {
        "type": "ai_response_done",
        "speech": speech,
        "notes": notes,
    }
    if mcq_data:
        done_payload["mcq"] = mcq_data
    await websocket.send_json(done_payload)

    # Generate TTS on the spoken dialogue ONLY
    try:
        spoken_dialogue = clean_text_for_tts(speech)
        if len(spoken_dialogue) > 900:
            spoken_dialogue = spoken_dialogue[:900].rsplit(" ", 1)[0] + "."
        if mcq_data and "question" in mcq_data:
            spoken_dialogue += " I've also placed a quick interactive check question on your screen to test this concept."

        audio_b64 = await generate_tts(spoken_dialogue)
        await websocket.send_json({"type": "ai_audio", "data": audio_b64, "text": speech})
    except Exception as tts_err:
        print(f"[TTS] Error: {tts_err}", flush=True)
        traceback.print_exc()
        await websocket.send_json({
            "type": "server_status",
            "message": "Voice playback unavailable — reading the text above instead.",
        })

    return full_text


def get_data_url_mimetype(data_url: str, fallback: str = "audio/webm") -> str:

    if data_url.startswith("data:") and ";" in data_url:
        return data_url[5:data_url.index(";")] or fallback
    return fallback


@router.websocket("/ws/learn/{session_id}")
async def learn_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    session = _get_session_or_close(session_id)
    if not session:
        await websocket.send_json({"type": "error", "message": "Session not found."})
        await websocket.close()
        return

    mode = session["config"].get("mode", "teach")  # "teach" or "doubt"

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            msg_type = payload.get("type")

            # ── Start: generate opening message ───────────────────────────────
            if msg_type == "start":
                session["status"] = "active"
                if not session.get("history"):
                    await websocket.send_json({"type": "server_status", "message": "Starting session..."})
                    try:
                        if mode == "teach":
                            stream_gen = stream_teach_response(session)
                        else:
                            stream_gen = stream_doubt_response(session)

                        ai_text = await _stream_and_speak(websocket, stream_gen, mode)
                        session["history"].append({"role": "assistant", "content": ai_text})
                        _save_sessions(sessions)

                    except Exception as e:
                        print(f"[Start] {e}")
                        traceback.print_exc()
                        await websocket.send_json({"type": "error", "message": f"Failed to start session: {e}"})
                else:
                    await websocket.send_json({"type": "server_status", "message": "Session ready."})

            # ── Audio: transcribe → generate response ─────────────────────────
            elif msg_type == "audio":
                try:
                    audio_str = payload["data"]
                    audio_mimetype = get_data_url_mimetype(audio_str)
                    if "," in audio_str:
                        audio_str = audio_str.split(",")[1]
                    audio_bytes = base64.b64decode(audio_str)

                    ts = datetime.now().strftime("%H:%M:%S")
                    print(f"[{ts}] [Audio] session={session_id} bytes={len(audio_bytes)}", flush=True)

                    await websocket.send_json({"type": "server_status", "message": "Transcribing..."})
                    transcript = await transcribe_audio(audio_bytes, audio_mimetype)
                    print(f"[{ts}] [STT] '{transcript}'", flush=True)

                    if not transcript or not transcript.strip():
                        await websocket.send_json({"type": "error", "message": "Could not hear you clearly. Please try again."})
                        continue

                    # Send transcript back so UI can show what the student said
                    await websocket.send_json({"type": "transcript", "text": transcript})

                    # Add to history as user turn
                    session["history"].append({"role": "user", "content": transcript})
                    _save_sessions(sessions)

                    # Generate AI response (streaming)
                    await websocket.send_json({"type": "server_status", "message": "Thinking..."})
                    if mode == "teach":
                        stream_gen = stream_teach_response(session)
                    else:
                        stream_gen = stream_doubt_response(session)

                    ai_text = await _stream_and_speak(websocket, stream_gen, mode)
                    session["history"].append({"role": "assistant", "content": ai_text})
                    _save_sessions(sessions)

                except Exception as e:
                    print(f"[Audio] {e}")
                    traceback.print_exc()
                    await websocket.send_json({"type": "error", "message": f"Audio processing failed: {e}"})

            # ── Text: typed message from student ─────────────────────────────
            elif msg_type == "text":
                try:
                    text_input = payload.get("text", "").strip()
                    if not text_input:
                        continue

                    ts = datetime.now().strftime("%H:%M:%S")
                    print(f"[{ts}] [Text] '{text_input}'", flush=True)

                    session["history"].append({"role": "user", "content": text_input})
                    _save_sessions(sessions)

                    await websocket.send_json({"type": "server_status", "message": "Thinking..."})
                    if mode == "teach":
                        stream_gen = stream_teach_response(session)
                    else:
                        stream_gen = stream_doubt_response(session)

                    ai_text = await _stream_and_speak(websocket, stream_gen, mode)
                    session["history"].append({"role": "assistant", "content": ai_text})
                    _save_sessions(sessions)


                except Exception as e:
                    print(f"[Text] {e}")
                    traceback.print_exc()
                    await websocket.send_json({"type": "error", "message": f"Processing failed: {e}"})

    except WebSocketDisconnect:
        print(f"[WS] Client disconnected: {session_id}")
        session["status"] = "ended"
    except Exception as e:
        print(f"[WS] Error: {e}")
        traceback.print_exc()
        try:
            await websocket.send_json({"type": "error", "message": f"Connection error: {e}"})
        except Exception:
            pass
