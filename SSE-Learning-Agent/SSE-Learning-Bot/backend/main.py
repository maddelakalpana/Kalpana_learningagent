from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from backend.api import routes, websocket
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SSE Learning Bot", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
templates = Jinja2Templates(directory=FRONTEND_DIR)

app.include_router(routes.router)
app.include_router(websocket.router)


@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import FileResponse
    favicon_path = os.path.join(FRONTEND_DIR, "assets", "sse-logo.svg")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/svg+xml")
    from fastapi.responses import Response
    return Response(status_code=204)


@app.get("/")
async def read_dashboard(request: Request):
    return templates.TemplateResponse(name="dashboard.html", request=request)


@app.get("/session/{session_id}")
@app.get("/learn/{session_id}")
async def read_session(request: Request, session_id: str):
    from backend.api.routes import sessions, _load_sessions
    if session_id not in sessions:
        sessions = _load_sessions()
    if session_id not in sessions:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(name="session.html", request=request, context={"session_id": session_id})
