# backend/ai/services/action_planner.py

import json
from typing import Any, Dict

from .ai_client import ask_llm  # use your existing client helper


SYSTEM_PROMPT = """
You are an action planner for an Event Management System (EMS).

You receive a single user message and must decide if it is asking to perform
a WRITE operation, and if so, extract the parameters.

Valid actions:
- "create_event"
- "update_event"
- "delete_event"
- "create_venue"
- "cancel_booking"
- "none"  (for purely informational / read-only questions)

You MUST respond with a single line of JSON and nothing else.

Schema:
{
  "action": "create_event" | "update_event" | "delete_event" | "create_venue" | "cancel_booking" | "none",
  "reason": "<short explanation of why you chose this action>",
  "params": {
      // key/value pairs needed to perform the action
  }
}

Guidelines:
- If you are not sure there is a write operation, use "action": "none".
- For create_event, try to extract:
  - title (string)
  - venue_name (string)
  - type (string, e.g. "Concert", "Sports", etc.)
  - capacity (integer if given)
  - ticket_price (float if given)
  - start (ISO8601 datetime string if possible)
  - end (ISO8601 datetime string if possible)
  - description (string, optional)
- For delete_event or update_event, include an "identifier" that may be an ID
  or an exact event title.
- For create_venue, include:
  - name
  - address (if provided)
  - capacity
  - type
- For cancel_booking, include:
  - booking_id (integer if the user mentions a specific booking id)
  

Additional CRITICAL rules:
- For any datetime field (like start_time, end_time), ALWAYS output values
  in the exact format: "YYYY-MM-DD HH:MM" (24-hour, no timezone).
  Example: "2025-12-05 19:00".
- NEVER use vague phrases like "next Friday" or "tomorrow 7pm" in JSON.
...
"""


def plan_action(message: str, is_organizer: bool) -> Dict[str, Any]:
    """
    Ask the LLM to classify the intent and extract structured parameters.

    If the user is NOT an organizer, you should still let the LLM suggest an
    action, but the caller will enforce permissions (i.e. disallow writes).
    """
    role_hint = (
        "The user is an organizer and can manage events and venues."
        if is_organizer
        else "The user is a participant and CANNOT create, edit, or delete events/venues."
    )

    user_prompt = f"{role_hint}\n\nUser message:\n```{message}```"

    # Use your existing ask_llm helper.
    response_text = ask_llm(
        SYSTEM_PROMPT,
        user_prompt,
        temperature=0.1,
    ).strip()

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        return {
            "action": "none",
            "reason": "Model did not return valid JSON.",
            "params": {},
        }

    action = data.get("action", "none")
    params = data.get("params") or {}
    reason = data.get("reason") or ""

    valid_actions = {
        "create_event",
        "update_event",
        "delete_event",
        "create_venue",
        "cancel_booking",
        "none",
    }
    if action not in valid_actions:
        action = "none"

    if not isinstance(params, dict):
        params = {}

    return {
        "action": action,
        "reason": reason,
        "params": params,
    }
