# FitCoach — a Fitness Q&A Agent (Phase 1)

A web app: a browser chat page talks to a Python backend, which calls
**Gemini via Google AI Studio** and returns the answer. Deployed to **Cloud Run**.

This is a learning project. The code is heavily commented to explain the *why*,
especially the AI-agent concepts (the stateless message loop, the system prompt,
separation of the agent from the web layer).

## Architecture

```
Browser (chat UI)  ──POST /api/chat {messages}──▶  FastAPI backend  ──▶  Gemini (AI Studio)
       ▲                                                  │
       └──────────────  reply  ◀──────────────────────────┘
```

- The **browser holds the conversation history** and sends it on every request,
  because the Messages API is stateless (it has no memory between calls).
- `app/agent.py` is the only file that talks to Gemini. RAG (Phase 2) plugs in there.

## Project layout

| File | Purpose |
|---|---|
| `app/prompts.py` | The fitness system prompt (the agent's persona + rules). |
| `app/agent.py`   | Builds the request and calls Gemini via Google AI Studio. |
| `app/main.py`    | FastAPI app: serves the page and `POST /api/chat`. |
| `app/static/index.html` | The chat UI (vanilla HTML/JS). |
| `Dockerfile`     | Container image for Cloud Run. |

## Branches

| Branch | LLM | Auth |
|---|---|---|
| `main` | Gemini (Google AI Studio) | `GOOGLE_API_KEY` |
| `anthropic-direct` | Claude (Anthropic API) | `ANTHROPIC_API_KEY` |
| `gemini-ai-studio` | Gemini (Google AI Studio) | `GOOGLE_API_KEY` |

---

## 1. One-time setup

Get a **Google AI Studio API key** at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
It's free with a generous rate limit — no billing required.

## 2. Run locally

```bash
# From the project root:
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements.txt

# Copy and fill in your API key:
cp .env.example .env
# Edit .env: set GOOGLE_API_KEY=AIzaSy...

# Start the dev server (auto-reloads on code changes):
.venv/bin/python -m uvicorn app.main:app --reload
```

Open <http://localhost:8000> and chat. Try a follow-up question to see that
multi-turn context works (the browser is resending the whole history).

## 3. Deploy to Cloud Run

```bash
gcloud run deploy fitness-qa \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=YOUR_API_KEY,MODEL_ID=gemini-2.0-flash,MAX_TOKENS=1024
```

Cloud Run builds the container from this folder and gives you a public HTTPS URL.

## Cost

Gemini 2.0 Flash has a **free tier** (no billing required for moderate usage).
Cloud Run scales to zero, so it costs nothing while idle.

## Phase 2 (next): RAG

Add a retrieval step inside `app/agent.py` — embed the user's question, search
your fitness documents, and fold the best matches into the prompt. The web layer
won't change.
