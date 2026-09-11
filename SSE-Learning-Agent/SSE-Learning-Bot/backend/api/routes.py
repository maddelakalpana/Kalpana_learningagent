"""API routes for AI Learning Assistant with session persistence."""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
import uuid
import io
import os
import json
from typing import Optional

router = APIRouter()

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".session_cache.json")


def _load_sessions() -> dict:
    """Load cached sessions from file if available."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_sessions(store: dict) -> None:
    """Save sessions store to cache file."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False)
    except Exception as e:
        print(f"[Session Cache Error] {e}")


# In-memory session store (seeded from cache)
sessions: dict = _load_sessions()


class StartSessionRequest(BaseModel):
    document_text: str
    topic_name: str
    mode: str  # "teach" or "doubt"


class TopicSearchRequest(BaseModel):
    topic: str
    model: Optional[str] = "nemotron"


from datetime import datetime
from backend.services.topic_search_service import synthesize_topic_content


@router.post("/api/topic/search-and-synthesize")
async def search_and_synthesize_topic(req: TopicSearchRequest):
    """Gather web search context via Tavily and synthesize study material using OpenRouter LLM."""
    topic = (req.topic or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic search term cannot be empty.")

    try:
        result = await synthesize_topic_content(topic=topic, model_choice=req.model or "nemotron")
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Topic synthesis failed: {str(e)}")



@router.post("/api/session/start")
async def start_session(req: StartSessionRequest):
    """Create a new learning session."""
    if req.mode not in ("teach", "doubt"):
        raise HTTPException(status_code=400, detail="mode must be 'teach' or 'doubt'")

    session_id = str(uuid.uuid4())
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sessions[session_id] = {
        "id": session_id,
        "status": "pending",
        "created_at": now_iso,
        "config": {
            "document_text": req.document_text,
            "topic_name": req.topic_name,
            "mode": req.mode,
        },
        "history": [],
    }
    _save_sessions(sessions)
    return {"success": True, "session_id": session_id}


@router.get("/api/sessions")
async def list_sessions():
    """List all saved learning sessions (newest first)."""
    global sessions
    sessions = _load_sessions()
    result = []
    for sid, s in sessions.items():
        result.append({
            "id": s["id"],
            "status": s.get("status", "active"),
            "topic_name": s.get("config", {}).get("topic_name", "Untitled Session"),
            "mode": s.get("config", {}).get("mode", "teach"),
            "created_at": s.get("created_at", "Recent"),
            "message_count": len(s.get("history", [])),
        })
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"sessions": result}


@router.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session details and conversation history for resumption."""
    global sessions
    if session_id not in sessions:
        sessions.update(_load_sessions())

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    return {
        "id": session["id"],
        "status": session.get("status", "pending"),
        "topic_name": session["config"]["topic_name"],
        "mode": session["config"]["mode"],
        "created_at": session.get("created_at", ""),
        "history": session.get("history", []),
        "message_count": len(session.get("history", [])),
    }


@router.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session from history."""
    global sessions
    if session_id in sessions:
        del sessions[session_id]
        _save_sessions(sessions)
        return {"success": True}
    raise HTTPException(status_code=404, detail="Session not found")



@router.post("/api/extract-text")
async def extract_text(file: UploadFile = File(...)):
    """Extract text from uploaded PDF, DOCX, TXT, or Markdown file."""
    contents = await file.read()
    filename = (file.filename or "").lower()

    try:
        if filename.endswith(".pdf"):
            import pdfplumber
            with pdfplumber.open(io.BytesIO(contents)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        elif filename.endswith(".docx"):
            from docx import Document
            document = Document(io.BytesIO(contents))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        elif filename.endswith((".txt", ".md")) or (file.content_type or "").startswith("text/"):
            text = contents.decode("utf-8", errors="ignore")
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload a PDF, DOCX, TXT, or Markdown file.",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Could not extract text from this file.")

    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No readable text was found in this file.")

    return {"text": text}


@router.get("/api/notifications")
async def get_notifications():
    """Return notifications (currently empty — silences 404 from browser extensions/polling)."""
    return {"notifications": [], "unread_count": 0}
