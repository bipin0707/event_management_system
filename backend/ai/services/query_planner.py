# backend/ai/services/query_planner.py

from typing import Any, Dict, List, Optional

from django.utils import timezone

from .ai_client import ask_llm, AIError
from events.models import Event
from bookings.models import Booking
from accounts.models import UserProfile


SYSTEM_PROMPT = """
You are an AI assistant for an Event Management System (EMS).

You are given:
- The current user (may be an organizer or a participant).
- A small snapshot of relevant data from the EMS database.
- The user's natural-language question.

Your job is to answer the question clearly and concisely, using ONLY the
information provided in the context plus general knowledge about how events
and bookings work. Do NOT invent extra events or bookings that are not in
the context.

If the user asks for something you cannot see in the context, say that you
don't see that information in the system snapshot and suggest what they
could do instead (e.g., ask the organizer, check another page, etc.).

Always speak in plain language, 1–3 short paragraphs, with bullet points
only when it truly helps readability.
"""


def _get_user_role(user) -> str:
    if not user or not user.is_authenticated:
        return "guest"

    try:
        profile: Optional[UserProfile] = user.userprofile
    except UserProfile.DoesNotExist:
        return "authenticated-participant"

    if profile.organizer:
        return "organizer"
    return "participant"


def _build_context_for_user(user) -> str:
    """
    Collect a small, human-readable snapshot of data to send to the LLM.

    This is intentionally compact to avoid blowing out the prompt.
    """
    now = timezone.now()
    role = _get_user_role(user)
    lines: List[str] = []

    lines.append(f"USER ROLE: {role}")
    if user and user.is_authenticated:
        lines.append(f"USER EMAIL: {user.email or 'unknown'}")
        lines.append(f"USERNAME: {user.get_username()}")

    # Upcoming published events (global)
    upcoming_events = (
        Event.objects.select_related("venue", "organizer")
        .filter(status="PUBLISHED", start_time__gte=now)
        .order_by("start_time")[:20]
    )

    if upcoming_events:
        lines.append("\nUPCOMING PUBLISHED EVENTS (max 20):")
        for ev in upcoming_events:
            lines.append(
                f"- Event #{ev.event_id}: '{ev.title}' "
                f"@ {ev.venue.name} ({ev.venue.type}), "
                f"starts {ev.start_time}, status={ev.status}, "
                f"capacity={ev.capacity}, price={ev.ticket_price}"
            )
    else:
        lines.append("\nUPCOMING PUBLISHED EVENTS: none found.")

    # Bookings related to this user (as participant)
    if user and user.is_authenticated and user.email:
        my_bookings = (
            Booking.objects.select_related("event", "customer")
            .filter(customer__email=user.email)
            .order_by("-booked_at")[:20]
        )
        if my_bookings:
            lines.append("\nBOOKINGS FOR THIS USER (max 20):")
            for b in my_bookings:
                lines.append(
                    f"- Booking #{b.booking_id} for event #{b.event.event_id} "
                    f"'{b.event.title}', tickets={b.ticket_qty}, "
                    f"status={b.status}, total={b.total_price}, "
                    f"booked_at={b.booked_at}"
                )
        else:
            lines.append("\nBOOKINGS FOR THIS USER: none found.")

    # If organizer, also show their events + booking counts
    if role == "organizer":
        try:
            organizer = user.userprofile.organizer
        except (UserProfile.DoesNotExist, AttributeError):
            organizer = None

        if organizer:
            org_events = (
                Event.objects.select_related("venue")
                .filter(organizer=organizer)
                .order_by("start_time")[:30]
            )
            if org_events:
                lines.append("\nEVENTS OWNED BY THIS ORGANIZER (max 30):")
                for ev in org_events:
                    booking_count = Booking.objects.filter(event=ev).count()
                    lines.append(
                        f"- Event #{ev.event_id}: '{ev.title}' "
                        f"@ {ev.venue.name} ({ev.venue.type}), "
                        f"starts {ev.start_time}, status={ev.status}, "
                        f"bookings={booking_count}, capacity={ev.capacity}, "
                        f"price={ev.ticket_price}"
                    )
            else:
                lines.append("\nEVENTS OWNED BY THIS ORGANIZER: none found.")

    return "\n".join(lines)


def answer_question(*args, **kwargs) -> str:
    """
    Main entry point used by ems_core.views.chat_api.

    It is deliberately flexible about arguments so it won't break if the view
    calls it positionally or with keywords.

    Expected usage (most likely):
        answer_question(user, message)
    or:
        answer_question(user=request.user, message=msg)
    """

    # --- Extract user & message robustly -----------------------------------
    user = None
    message = ""

    if len(args) >= 1:
        user = args[0]
    if len(args) >= 2:
        message = args[1]

    # Keyword overrides
    if "user" in kwargs:
        user = kwargs["user"]
    if "message" in kwargs:
        message = kwargs["message"]
    elif "query" in kwargs:
        message = kwargs["query"]

    message = (message or "").strip()
    if not message:
        return "I didn't receive a question. Please type what you'd like to know about your events or bookings."

    # --- Build context snapshot -------------------------------------------
    context_text = _build_context_for_user(user)

    user_prompt = (
        f"Here is a snapshot of the EMS database relevant to the current user:\n\n"
        f"---BEGIN CONTEXT---\n{context_text}\n---END CONTEXT---\n\n"
        f"User question:\n{message}\n\n"
        f"Answer using only the context above and general event-management knowledge."
    )

    try:
        reply = ask_llm(
            SYSTEM_PROMPT,
            user_prompt,
            temperature=0.2,
        )
        return reply.strip()
    except AIError:
        return (
            "I had trouble contacting the AI backend. "
            "Please try again in a moment."
        )
    except Exception:
        # Avoid leaking stack traces to the user
        return (
            "Something went wrong while answering your question. "
            "Please try again or contact the administrator if it persists."
        )


# ---------------------------------------------------------------------------
# Backwards-compatibility shim for older code that imports `plan_query`.
# This wraps the newer `answer_question` helper.
# ---------------------------------------------------------------------------

def plan_query(user, message: str) -> Dict[str, Any]:
    """
    Lightweight wrapper so existing code that calls `plan_query` keeps working.

    Returns a dict so callers can do:
        result = plan_query(user, message)
        text = result["answer"]
    """
    return {
        "answer": answer_question(user=user, message=message),
    }
