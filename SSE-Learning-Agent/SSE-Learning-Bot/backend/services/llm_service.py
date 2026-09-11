"""LLM service for AI Learning Assistant with Google Gemini and proxy support."""
import os
import httpx
from dotenv import load_dotenv
from backend.config import settings

load_dotenv()

# ==============================================================================
# Prompts for Progressive Teaching and Doubt Resolution
# ==============================================================================

TEACH_SYSTEM = """You are an engaging, patient, and knowledgeable AI Professor conducting a live 1-on-1 teaching lesson with a student.

TOPIC: {topic_name}
REFERENCE DOCUMENT:
---
{document_text}
---

CRITICAL DUAL-OUTPUT FORMAT:
Every response you produce MUST be split into two distinct blocks so that spoken voice dialogue and written chat notes are separate:

1. [SPEECH]...[/SPEECH]
   - What you speak aloud to the student.
   - Write 2 to 4 natural, engaging conversational sentences explaining the concept.
   - Speak naturally without bullet points, asterisks, or markdown symbols.
   - End with an engaging check-in.

2. [NOTES]...[/NOTES]
   - The written study summary that appears in the student's chat notebook.
   - Provide a clear, high-yield summary:
     • **Key Concept**: 1 concise sentence definition.
     • **How it Works / Example**: 1 concise explanation sentence.
     • **Key Takeaway**: Important rule or behavior to remember.
     💡 **Key Insight**: A practical pro-tip, common pitfall, or high-yield insight.

3. [MCQ]...[/MCQ] (Include on turns after the opening turn):
   - Place an interactive check question at the very end:
[MCQ]
{{
  "question": "Question text testing the concept just taught",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "answer_index": 0,
  "explanation": "Clear explanation of why this option is correct."
}}
[/MCQ]
"""

DOUBT_SYSTEM = """You are an expert AI Tutor specialized in resolving student doubts.

TOPIC: {topic_name}
REFERENCE DOCUMENT:
---
{document_text}
---

CRITICAL DUAL-OUTPUT FORMAT:
Every response you produce MUST be split into two distinct blocks:

1. [SPEECH]...[/SPEECH]
   - What you speak aloud to the student.
   - 2 to 3 natural, direct conversational sentences answering their doubt clearly without bullet points.

2. [NOTES]...[/NOTES]
   - The written study summary for the chat notebook:
     • **Doubt Summary**: Direct 1-sentence resolution.
     • **Core Rule**: Important takeaway to remember.
     💡 **Key Insight**: Why students often get confused and how to avoid the trap.

3. [MCQ]...[/MCQ]
   - Interactive verification question at the end:
[MCQ]
{{
  "question": "Quick question verifying the concept just explained",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "answer_index": 1,
  "explanation": "Clear explanation of why this answer is correct."
}}
[/MCQ]
"""




def _get_gemini_key() -> str:
    """Return Google Gemini API key if present and valid."""
    key = getattr(settings, "gemini_api_key", "") or os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    key = key.strip().strip('"').strip("'")
    if key and not key.startswith("sk-litellm") and len(key) >= 20:
        return key
    return ""


async def _call_gemini_api(prompt: str, system_instruction: str) -> str:
    """Call Google Gemini REST API (non-streaming)."""
    api_key = _get_gemini_key()
    model = getattr(settings, "gemini_model", "") or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1500}
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    async with httpx.AsyncClient(timeout=25.0) as client:
        res = await client.post(url, json=payload)
        if res.status_code != 200:
            raise RuntimeError(f"Gemini API error ({res.status_code}): {res.text}")
        data = res.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("No candidates in Gemini response")
        parts = candidates[0].get("content", {}).get("parts", [])
        return parts[0].get("text", "").strip()


async def _stream_gemini_api(prompt: str, system_instruction: str):
    """Stream Google Gemini REST API — yields text chunks as they arrive."""
    import json as _json

    api_key = _get_gemini_key()
    model = getattr(settings, "gemini_model", "") or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={api_key}"

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1500}
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, json=payload) as response:
            if response.status_code != 200:
                error_body = await response.aread()
                raise RuntimeError(f"Gemini stream error ({response.status_code}): {error_body.decode()}")

            buffer = ""
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                json_str = line[6:].strip()
                if not json_str:
                    continue
                try:
                    data = _json.loads(json_str)
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            text = part.get("text", "")
                            if text:
                                buffer += text
                                yield text
                except _json.JSONDecodeError:
                    continue


async def _call_openai_or_proxy(system_prompt: str, history: list, default_user_prompt: str) -> str:
    """Call OpenAI or configured LiteLLM proxy."""
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if not openai_key:
        raise ValueError("No LLM credentials configured. Please set GEMINI_API_KEY or OPENAI_API_KEY in .env.")

    from openai import AsyncOpenAI
    base_url = (os.getenv("BASE_URL") or "https://api.openai.com/v1").strip('"').strip("'")
    client = AsyncOpenAI(api_key=openai_key, base_url=base_url)

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    if not history:
        messages.append({"role": "user", "content": default_user_prompt})

    model = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
    res = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=1500,
        temperature=0.7,
    )
    return res.choices[0].message.content.strip()


def _build_teach_prompt(session_data: dict):
    """Build system prompt and user prompt for teach mode. Returns (system_prompt, user_prompt)."""
    config = session_data["config"]
    history = session_data.get("history", [])

    system_prompt = TEACH_SYSTEM.format(
        topic_name=config.get("topic_name", "the study topic"),
        document_text=config.get("document_text", "")[:7000],
    )

    conversation_text = ""
    for msg in history[-8:]:
        role = "Student" if msg["role"] == "user" else "Professor"
        conversation_text += f"{role}: {msg['content']}\n"

    if not history:
        prompt = (
            "Start the lesson! Greet the student, provide a brief roadmap of the main concepts "
            "we will cover, explain Concept #1 engagingly with an analogy, and end with an open check-in. "
            "Do NOT include an MCQ on this first turn."
        )
    else:
        prompt = (
            f"Conversation so far:\n{conversation_text}\n"
            "Acknowledge the student's response with 1 encouraging sentence, teach the next concept "
            "in 3-4 clear, complete sentences, and include an interactive [MCQ] block testing that concept."
        )

    return system_prompt, prompt


def _build_doubt_prompt(session_data: dict):
    """Build system prompt and user prompt for doubt mode. Returns (system_prompt, user_prompt)."""
    config = session_data["config"]
    history = session_data.get("history", [])

    system_prompt = DOUBT_SYSTEM.format(
        topic_name=config.get("topic_name", "the study topic"),
        document_text=config.get("document_text", "")[:7000],
    )

    conversation_text = ""
    for msg in history[-8:]:
        role = "Student" if msg["role"] == "user" else "Tutor"
        conversation_text += f"{role}: {msg['content']}\n"

    if not history:
        prompt = (
            "Greet the student warmly in 2-3 sentences and mention 2 or 3 common questions/confusions about this topic "
            "to help them get started. Do not include an MCQ."
        )
    else:
        prompt = (
            f"Conversation history:\n{conversation_text}\n"
            "Answer the student's doubt directly and thoroughly in 3-5 complete sentences with an example, "
            "and provide an interactive [MCQ] block testing that concept."
        )

    return system_prompt, prompt


async def generate_teach_response(session_data: dict) -> str:
    """Generate progressive teaching response (non-streaming)."""
    system_prompt, prompt = _build_teach_prompt(session_data)
    history = session_data.get("history", [])

    gemini_key = _get_gemini_key()
    if gemini_key:
        try:
            return await _call_gemini_api(prompt, system_prompt)
        except Exception as e:
            print(f"[LLM] Gemini API error: {e}. Using proxy fallback...", flush=True)

    return await _call_openai_or_proxy(system_prompt, history, "Please begin the lesson.")


async def generate_doubt_response(session_data: dict) -> str:
    """Generate doubt resolution response (non-streaming)."""
    system_prompt, prompt = _build_doubt_prompt(session_data)
    history = session_data.get("history", [])

    gemini_key = _get_gemini_key()
    if gemini_key:
        try:
            return await _call_gemini_api(prompt, system_prompt)
        except Exception as e:
            print(f"[LLM] Gemini API error: {e}. Using proxy fallback...", flush=True)

    return await _call_openai_or_proxy(system_prompt, history, "Please resolve my doubt.")


async def stream_teach_response(session_data: dict):
    """Stream progressive teaching response — yields text chunks with fallbacks."""
    system_prompt, prompt = _build_teach_prompt(session_data)

    gemini_key = _get_gemini_key()
    if gemini_key:
        try:
            chunk_yielded = False
            async for chunk in _stream_gemini_api(prompt, system_prompt):
                chunk_yielded = True
                yield chunk
            if chunk_yielded:
                return
        except Exception as e:
            print(f"[Stream] Gemini stream error: {e}. Falling back to non-streaming API...", flush=True)

        try:
            full_text = await _call_gemini_api(prompt, system_prompt)
            yield full_text
            return
        except Exception as e:
            print(f"[LLM] Gemini non-streaming fallback error: {e}. Using proxy...", flush=True)

    # Fallback: non-streaming proxy, yield entire response at once
    history = session_data.get("history", [])
    result = await _call_openai_or_proxy(system_prompt, history, "Please begin the lesson.")
    yield result


async def stream_doubt_response(session_data: dict):
    """Stream doubt resolution response — yields text chunks with fallbacks."""
    system_prompt, prompt = _build_doubt_prompt(session_data)

    gemini_key = _get_gemini_key()
    if gemini_key:
        try:
            chunk_yielded = False
            async for chunk in _stream_gemini_api(prompt, system_prompt):
                chunk_yielded = True
                yield chunk
            if chunk_yielded:
                return
        except Exception as e:
            print(f"[Stream] Gemini stream error: {e}. Falling back to non-streaming API...", flush=True)

        try:
            full_text = await _call_gemini_api(prompt, system_prompt)
            yield full_text
            return
        except Exception as e:
            print(f"[LLM] Gemini non-streaming fallback error: {e}. Using proxy...", flush=True)

    # Fallback: non-streaming proxy, yield entire response at once
    history = session_data.get("history", [])
    result = await _call_openai_or_proxy(system_prompt, history, "Please resolve my doubt.")
    yield result


