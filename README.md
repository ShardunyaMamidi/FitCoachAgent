# FitCoach — a Fitness Q&A Agent (Phase 1)

A small web app: a browser chat page talks to a Python backend, which calls
**Claude on Google Vertex AI** and returns the answer. Deployed to **Cloud Run**.

This is a learning project. The code is heavily commented to explain the *why*,
especially the AI-agent concepts (the stateless message loop, the system prompt,
separation of the agent from the web layer).

## Architecture

```
Browser (chat UI)  ──POST /api/chat {messages}──▶  FastAPI backend  ──▶  Claude (Vertex AI)
       ▲                                                  │
       └──────────────  reply  ◀──────────────────────────┘
```

- The **browser holds the conversation history** and sends it on every request,
  because the Messages API is stateless (it has no memory between calls).
- `app/agent.py` is the only file that talks to Claude. RAG (Phase 2) plugs in there.

## Project layout

| File | Purpose |
|---|---|
| `app/prompts.py` | The fitness system prompt (the agent's persona + rules). |
| `app/agent.py`   | Builds the request and calls Claude on Vertex AI. |
| `app/main.py`    | FastAPI app: serves the page and `POST /api/chat`. |
| `app/static/index.html` | The chat UI (vanilla HTML/JS). |
| `Dockerfile`     | Container image for Cloud Run. |

---

## 1. One-time GCP setup

You'll run these yourself (they need your Google login / a browser).

```bash
# Pick or create a project, and set it as the default.
gcloud config set project YOUR_PROJECT_ID

# Enable the Vertex AI API.
gcloud services enable aiplatform.googleapis.com

# Authenticate locally so the app can call Vertex via Application Default Credentials.
gcloud auth application-default login
```

You also need to **enable the Claude model** once in the Vertex AI Model Garden
(search "Claude" there and enable the model you plan to use), and make sure
**billing is enabled** on the project (this activates the $300 free trial credit).

## 2. Run locally

```bash
# From the project root:
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Tell the app which project/model to use (see .env.example):
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
export VERTEX_REGION=global
export MODEL_ID=claude-opus-4-8

# Start the dev server (auto-reloads on code changes):
uvicorn app.main:app --reload
```

Open <http://localhost:8000> and chat. Try a follow-up question to see that
multi-turn context works (the browser is resending the whole history).

## 3. Deploy to Cloud Run

```bash
gcloud run deploy fitness-qa \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,VERTEX_REGION=global,MODEL_ID=claude-opus-4-8
```

Cloud Run builds the container from this folder and gives you a public HTTPS URL.

**The key auth difference to understand:** locally the app uses *your* ADC
credentials; on Cloud Run it uses the service's **service account**. That account
needs permission to call Vertex AI. Grant it the Vertex AI User role:

```bash
PROJECT_ID=YOUR_PROJECT_ID
# Find the service account your Cloud Run service runs as (often the default
# compute service account), then grant it Vertex access:
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

## Cost

Each Q&A is roughly a penny on Opus 4.8 (less on Haiku). The $300 free-trial
credit covers far more usage than a learning project will ever generate. Cloud Run
scales to zero, so it costs nothing while idle.

## Phase 2 (next): RAG

Add a retrieval step inside `app/agent.py` — embed the user's question, search
your fitness documents, and fold the best matches into the prompt. The web layer
won't change.
