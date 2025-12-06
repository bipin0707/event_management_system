# backend/ai/services/ai_client.py

import json
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Ollama local chat endpoint
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
# Adjust to match your pulled model name
MODEL_NAME = "llama3.1:latest"


class AIError(Exception):
    """Custom exception for AI-related errors."""
    pass


def ask_llm(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    """
    High-level wrapper around the local Llama 3.1 (Ollama) chat API.

    Parameters
    ----------
    system_prompt : str
        Instructions / role message for the model.
    user_prompt : str
        The actual question or text from the user.
    temperature : float, optional
        Sampling temperature (0.0 = very deterministic, higher = more random).

    Returns
    -------
    str
        The assistant's reply text.

    Raises
    ------
    AIError
        If there is a network issue, non-200 response, or invalid JSON.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    payload: dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,  # we want a single JSON object back
        "options": {
            "temperature": temperature,
        },
    }

    try:
        response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=180)
    except requests.RequestException as exc:
        logger.exception("Error connecting to Ollama")
        raise AIError("Could not reach local AI service (Ollama).") from exc

    if response.status_code != 200:
        logger.error("Ollama returned status %s: %s", response.status_code, response.text)
        raise AIError(f"AI service error: HTTP {response.status_code}")

    # For stream=False, Ollama returns a single JSON object with a "message" field
    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        logger.exception("Invalid JSON from Ollama")
        raise AIError("Invalid response from AI service.") from exc

    message = data.get("message") or {}
    content = message.get("content")
    if not content:
        logger.warning("No 'content' in Ollama response: %s", data)
        raise AIError("AI service returned an empty response.")

    return content.strip()
