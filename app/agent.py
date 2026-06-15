"""
The AGENT CORE — the only place that talks to the LLM.

This module is deliberately small and isolated. The web layer (main.py) calls
`answer(messages)` and gets back a string. It does NOT know about model
IDs, or prompts. That separation means swapping the LLM provider (Vertex AI,
Anthropic, Gemini) only ever touches THIS file.

KEY AI-AGENT CONCEPT — the API is stateless:
    The LLM does not remember previous turns. Every call sends the *entire*
    conversation history (the `messages` list). "Memory" is just us resending
    that list each time. Here, the browser keeps the history and sends it on every
    request, so this function stays stateless — which is also exactly what a
    serverless host like Cloud Run wants.

NOTE ON MESSAGE FORMAT:
    Our API uses {"role": "user"/"assistant", "content": "..."}.
    Gemini uses  {"role": "user"/"model",      "parts": [{"text": "..."}]}.
    We convert between them inside answer() so the rest of the app is unaware.
"""

import os
import functools

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .prompts import FITNESS_SYSTEM_PROMPT

load_dotenv()

# --- Configuration (read from environment variables) --------------------------
#
#   GEMINI_API_KEY : your Google AI Studio API key (required).
#                   Get one at aistudio.google.com/apikey
#   MODEL_ID       : which Gemini model to use.
#                   "gemini-2.0-flash" is fast and has a generous free tier.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_ID = os.environ.get("MODEL_ID", "gemini-2.0-flash")

MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))


@functools.lru_cache(maxsize=1)
def _client() -> genai.Client:
    """Build the Gemini client once and reuse it."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Get one at aistudio.google.com/apikey "
            "and add it to your .env file."
        )
    return genai.Client(api_key=GEMINI_API_KEY)


def _to_gemini_history(messages: list[dict]) -> list[types.Content]:
    """
    Convert our internal message format to Gemini's Content format.

    Our format:  {"role": "user"/"assistant", "content": "text"}
    Gemini needs: Content(role="user"/"model", parts=[Part(text="text")])

    The role rename (assistant → model) is the key difference — Gemini calls
    the AI's turns "model" instead of "assistant".
    """
    role_map = {"user": "user", "assistant": "model"}
    return [
        types.Content(
            role=role_map[m["role"]],
            parts=[types.Part(text=m["content"])],
        )
        for m in messages
    ]


def answer(messages: list[dict]) -> str:
    """
    Send the conversation to Gemini and return the reply text.

    PHASE 2 HOOK: retrieval goes here. Inject retrieved snippets into the
    system prompt before calling the model. The signature won't change, so
    main.py and the browser stay untouched.
    """
    response = _client().models.generate_content(
        model=MODEL_ID,
        contents=_to_gemini_history(messages),
        config=types.GenerateContentConfig(
            system_instruction=FITNESS_SYSTEM_PROMPT,
            max_output_tokens=MAX_TOKENS,
        ),
    )
    return response.text
