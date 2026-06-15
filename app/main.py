"""
The WEB LAYER — a tiny FastAPI app that:
  1. serves the chat page (GET /), and
  2. accepts chat requests (POST /api/chat) and forwards them to the agent.

It knows nothing about Claude or Vertex — it just validates input, calls
`agent.answer()`, and returns the reply as JSON. Keeping the web layer this thin
is what lets us evolve the agent independently.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import agent

app = FastAPI(title="FitCoach — Fitness Q&A Agent")

STATIC_DIR = Path(__file__).parent / "static"


# --- Request/response shapes --------------------------------------------------
# Pydantic models validate incoming JSON for us: if the browser sends something
# malformed, FastAPI rejects it with a clear 422 error before our code runs.
class Message(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")  # only these two roles allowed
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class ChatResponse(BaseModel):
    reply: str


# --- Routes -------------------------------------------------------------------
@app.get("/")
def index() -> FileResponse:
    """Serve the single-page chat UI."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz")
def healthz() -> dict:
    """A trivial health check — handy for confirming the server is up."""
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """
    Take the full conversation history from the browser, ask the agent, and return
    the reply. We convert the validated Pydantic models back into plain dicts,
    which is the shape the Anthropic SDK expects.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    history = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        reply = agent.answer(history)
    except Exception as exc:  # noqa: BLE001 — surface a clean error to the UI
        # In a learning project we keep this simple. In production you'd log the
        # full exception server-side and return a generic message to the client.
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    return ChatResponse(reply=reply)
