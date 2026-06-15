"""
The AGENT CORE — the only place that talks to Claude.

This module is deliberately small and isolated. The web layer (main.py) calls
`answer(messages)` and gets back a string. It does NOT know about Vertex, model
IDs, or prompts. That separation is what makes Phase 2 (RAG) easy: we'll add a
retrieval step *inside this file* without touching the web layer at all.

KEY AI-AGENT CONCEPT — the API is stateless:
    Claude does not remember previous turns. Every call sends the *entire*
    conversation history (the `messages` list). "Memory" is just us resending
    that list each time. Here, the browser keeps the history and sends it on every
    request, so this function stays stateless — which is also exactly what a
    serverless host like Cloud Run wants.
"""

import os
import functools

from dotenv import load_dotenv
from anthropic import AnthropicVertex

from .prompts import FITNESS_SYSTEM_PROMPT

load_dotenv()

# --- Configuration (read from environment variables) --------------------------
# We read config from env vars so the SAME code runs locally and on Cloud Run —
# only the values differ. This is a core twelve-factor / cloud habit.
#
#   GOOGLE_CLOUD_PROJECT : your GCP project ID (required).
#   VERTEX_REGION        : "global" is recommended (best availability, no premium).
#   MODEL_ID             : which Claude model to use. "claude-haiku-4-5@20251001" is
#                          cheap and fast; swap to "claude-opus-4-8" for most capable.
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
VERTEX_REGION = os.environ.get("VERTEX_REGION", "global")
MODEL_ID = os.environ.get("MODEL_ID", "claude-haiku-4-5@20251001")

# Cap on how long a single reply can be. Plenty for a chat answer; keeps cost and
# latency bounded. (Tokens ≈ word-pieces; ~1024 tokens is a few solid paragraphs.)
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))


@functools.lru_cache(maxsize=1)
def _client() -> AnthropicVertex:
    """
    Build the Vertex client once and reuse it (lru_cache makes this a singleton).

    We build it lazily — on first use rather than at import time — so that simply
    importing this module doesn't fail if credentials aren't set up yet. The client
    authenticates using Google's Application Default Credentials (ADC):
      - Locally: the credentials from `gcloud auth application-default login`.
      - On Cloud Run: the service's attached service account.
    """
    if not PROJECT_ID:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT is not set. Set it to your GCP project ID "
            "(see .env.example) before starting the server."
        )
    return AnthropicVertex(project_id=PROJECT_ID, region=VERTEX_REGION)


def answer(messages: list[dict]) -> str:
    """
    Send the conversation to Claude and return the assistant's reply text.

    `messages` is the full history, e.g.:
        [{"role": "user", "content": "How do I start lifting?"},
         {"role": "assistant", "content": "..."},
         {"role": "user", "content": "Make it 3 days a week"}]

    PHASE 2 HOOK: this is where retrieval will go. Before calling Claude, we'll
    look up relevant snippets from your fitness documents and fold them into the
    request (e.g. appended to the system prompt). The signature won't change, so
    main.py and the browser stay untouched.
    """
    response = _client().messages.create(
        model=MODEL_ID,
        max_tokens=MAX_TOKENS,
        system=FITNESS_SYSTEM_PROMPT,
        messages=messages,
    )

    # A response's `content` is a list of typed blocks. For a normal text reply
    # there's a single "text" block, but we join all text blocks to be safe.
    return "".join(block.text for block in response.content if block.type == "text")
