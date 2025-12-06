from decimal import Decimal
import json

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Sum
from django.shortcuts import render, get_object_or_404

from ai.services.ai_client import ask_llm, AIError
from ai.services.query_planner import plan_query  # your existing read planner
from ai.services.action_planner import plan_action
from ai.models import PendingAIAction

from events.models import Event, Organizer, Venue
from bookings.models import Booking
from accounts.models import UserProfile
from ai.services.query_planner import answer_question
from django.core.exceptions import ValidationError


def home(request):
    """
    Home page with a small preview of upcoming events.
    """
    events = (
        Event.objects.select_related("venue")
        .filter(status="PUBLISHED", start_time__gte=timezone.now())
        .order_by("start_time")[:3]
    )
    return render(request, "home.html", {"events": events})


@login_required
def chat_page(request):
    """
    Render the chatbot page. Conversation handled via AJAX /chat/api/.
    """
    return render(request, "chat/chat_page.html")


# ---------- Helper to get organizer ----------

def _get_user_organizer(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return None
    return profile.organizer


# ---------- Internal helper: execute create_event pending action ----------

def _execute_create_event(pending: PendingAIAction, user):
    """
    Commit a previously planned create_event action.

    pending.payload is expected to contain the "fields" dict from the planner.
    """
    organizer = _get_user_organizer(type("Req", (), {"user": user})())
    if not organizer:
        pending.delete()
        return "You are not registered as an organizer, so I cannot create events for you."

    fields = pending.payload or {}
    title = fields.get("title") or "Untitled event"
    description = fields.get("description") or ""

    # Event type / venue type
    event_type = fields.get("type") or None  # Exhibition|Conference|Concert|Sports
    venue_type = fields.get("venue_type") or event_type

    # Simple mapping: if no venue_type, default based on event_type
    if venue_type is None and event_type in ("Exhibition", "Conference", "Concert", "Sports"):
        venue_type = event_type

    # Dates come as free-form strings from LLM; we will try to parse them,
    # but if parsing fails we abort safely.
    from datetime import datetime
    from django.utils import timezone as dj_tz

    def parse_dt(value):
        if not value:
            return None
        text = str(value).strip().replace("T", " ")
        # Try a few simple formats
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(text, fmt)
                return dj_tz.make_aware(dt)
            except ValueError:
                continue
        # As last resort, try fromisoformat (may still fail)
        try:
            dt = datetime.fromisoformat(str(value))
            if dj_tz.is_naive(dt):
                dt = dj_tz.make_aware(dt)
            return dt
        except Exception:
            return None

    start_time = parse_dt(fields.get("start_time"))
    end_time = parse_dt(fields.get("end_time"))

    capacity = fields.get("capacity")
    try:
        capacity = int(capacity) if capacity is not None else None
    except (TypeError, ValueError):
        capacity = None

    status = fields.get("status") or "PUBLISHED"

    # Ticket price required for Concert / Sports
    ticket_price = fields.get("ticket_price")
    try:
        if ticket_price is not None:
            ticket_price = Decimal(str(ticket_price))
    except Exception:
        ticket_price = None

    if event_type in ("Concert", "Sports") and (ticket_price is None or ticket_price <= 0):
        pending.delete()
        return (
            "I tried to create a Concert/Sports event but the ticket price was missing or invalid. "
            "Please specify a valid positive ticket price."
        )

    # Venue resolution: use venue_id if provided, else create a new venue
    venue = None
    venue_id = fields.get("venue_id")
    if venue_id is not None:
        try:
            venue = Venue.objects.get(pk=venue_id)
        except Venue.DoesNotExist:
            venue = None

    if venue is None:
        venue_name = fields.get("venue_name") or "Unnamed venue"
        venue_address = fields.get("venue_address") or ""
        venue_capacity = capacity or 0
        venue_type_final = venue_type or "Conference"  # safe default

        venue = Venue.objects.create(
            name=venue_name,
            address=venue_address,
            capacity=venue_capacity,
            type=venue_type_final,
        )

    # Now actually create the Event (this will run model validation)
    event = Event(
        organizer=organizer,
        venue=venue,
        title=title,
        description=description,
        start_time=start_time,
        end_time=end_time,
        capacity=capacity,
        status=status,
        ticket_price=ticket_price,
    )

    from django.core.exceptions import ValidationError

    try:
        event.full_clean()
    except ValidationError as exc:
        pending.delete()
        return (
            "I tried to create the event but validation failed: "
            f"{exc.message_dict}"
        )

    event.save()
    pending.delete()

    return (
        f"Done! I created the event **{event.title}** at **{event.venue.name}**.\n\n"
        f"- Starts: {event.start_time}\n"
        f"- Ends: {event.end_time}\n"
        f"- Capacity: {event.capacity if event.capacity is not None else 'Not set'}\n"
        f"- Ticket price: {event.ticket_price if event.ticket_price else 'Free / not set'}\n"
        "You can further edit this event from the Organizer dashboard."
    )


# ---------- Chat API: preview + confirm + read logic ----------
@csrf_exempt
@require_POST
@login_required
def chat_api(request):
    """
    Main AI entrypoint.

    Behaviour:
    1. If there is a pending action for this user:
       - "yes"/"confirm" -> execute it
       - "no"/"cancel"   -> discard it
    2. Otherwise, call the action planner:
       - if action == "none" -> pure Q&A (read-only assistant)
       - else                -> store PendingAIAction + return a preview
    """
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    message = (body.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "Message is required."}, status=400)

    user = request.user
    normalized = message.lower().strip()

    # ------------------------------------------------------------------
    # 1) Check for existing pending action (confirmation workflow)
    # ------------------------------------------------------------------
    pending = (
        PendingAIAction.objects
        .filter(user=user)
        .order_by("-created_at")
        .first()
    )

    # Drop expired
    if pending and pending.is_expired():
        pending.delete()
        pending = None

    confirm_phrases = {"yes", "y", "confirm", "ok", "okay", "do it", "go ahead"}
    cancel_phrases = {"no", "n", "cancel", "stop", "never mind", "abort"}

    if pending and normalized in confirm_phrases:
        reply = _execute_pending_action(pending, user)
        pending.delete()
        return JsonResponse({"reply": reply})

    if pending and normalized in cancel_phrases:
        pending.delete()
        return JsonResponse({
            "reply": "Okay, I’ve cancelled that action and won’t make any changes."
        })

    # If there *is* a pending action but the user says something else,
    # we can gently remind them while still answering the new query.
    reminder_text = None
    if pending:
        reminder_text = (
            "You still have a pending action waiting for confirmation.\n\n"
            "If you’d like to proceed, type **yes**. To cancel, type **no**.\n\n"
            "I’ll also treat your new message as a separate question."
        )

    # ------------------------------------------------------------------
    # 2) No-confirmation branch -> use action planner
    # ------------------------------------------------------------------
    is_organizer = False
    try:
        profile = user.userprofile
        is_organizer = bool(profile.organizer)
    except UserProfile.DoesNotExist:
        pass

    plan = plan_action(message, is_organizer=is_organizer)
    action = plan.get("action", "none")
    params = plan.get("params") or {}
    reason = plan.get("reason") or ""

    # If no write action -> normal Q&A
    if action == "none":
        answer = answer_question(user=user, message=message)
        if reminder_text:
            answer = f"{reminder_text}\n\n---\n\n{answer}"
        return JsonResponse({"reply": answer})

    # Non-organizers are not allowed to perform write actions
    if not is_organizer:
        return JsonResponse({
            "reply": (
                "It looks like you’re asking me to modify events or bookings, "
                "but you’re not registered as an organizer. "
                "You can still ask me questions about events and your own bookings."
            )
        })

    # ------------------------------------------------------------------
    # 3) Store PendingAIAction and return a preview
    # ------------------------------------------------------------------
    pending = PendingAIAction.create_for(
        user=user,
        action_type=action,
        payload=params,
        minutes=5,
    )

    preview_lines = [f"Here’s what I plan to do (`{action}`):", ""]

    if action == "create_event":
        title = params.get("title", "(missing title)")
        venue_name = params.get("venue_name", "(venue not specified)")
        start = params.get("start")
        end = params.get("end")
        capacity = params.get("capacity")
        price = params.get("ticket_price")
        description = params.get("description")

        preview_lines.append(f"• **Title** (required): {title}")
        preview_lines.append(f"• **Venue** (required): {venue_name}")
        if start:
            preview_lines.append(f"• **Starts at**: {start}")
        if end:
            preview_lines.append(f"• **Ends at**: {end}")
        if capacity is not None:
            preview_lines.append(f"• **Capacity**: {capacity}")
        if price is not None:
            preview_lines.append(f"• **Ticket price**: ${price}")
        if description:
            preview_lines.append(f"• Description: {description}")

    elif action == "delete_event":
        preview_lines.append(
            f"• Delete the event identified by: {params.get('identifier', '(no identifier)')}"
        )

    elif action == "update_event":
        preview_lines.append(
            f"• Update the event identified by: {params.get('identifier', '(no identifier)')}"
        )
        changes = {k: v for k, v in params.items() if k != "identifier"}
        preview_lines.append(f"• With changes: {changes}")

    elif action == "create_venue":
        preview_lines.append(
            f"• Create a **venue** named: {params.get('name', '(missing name)')}"
        )
        addr = params.get("address")
        if addr:
            preview_lines.append(f"• Address: {addr}")
        cap = params.get("capacity")
        if cap is not None:
            preview_lines.append(f"• Capacity: {cap}")
        vtype = params.get("type")
        if vtype:
            preview_lines.append(f"• Type: {vtype}")

    elif action == "cancel_booking":
        preview_lines.append(
            f"• Cancel booking with ID: {params.get('booking_id', '(missing id)')}"
        )

    preview_lines.append("")
    preview_lines.append("If this looks correct, type **yes** to confirm. To cancel, type **no**.")

    if reason:
        preview_lines.append("")
        preview_lines.append(f"_Why I chose this action_: {reason}")

    text = "\n".join(preview_lines)
    return JsonResponse({"reply": text})


def _execute_pending_action(pending: PendingAIAction, user) -> str:
    """
    Actually perform the DB changes for a confirmed pending action.
    Returns a human-readable message describing the result.
    """
    params = pending.payload or {}
    action = pending.action_type

    # Organizer for this user (needed for permissions)
    organizer = None
    try:
        profile = user.userprofile
        organizer = profile.organizer
    except (UserProfile.DoesNotExist, Organizer.DoesNotExist, AttributeError):
        pass

    if action == "create_event":
        if not organizer:
            return (
                "I couldn’t find an organizer profile linked to your account, "
                "so I can’t create the event."
            )

        title = params.get("title") or "Untitled event"
        venue_name = params.get("venue_name")

        if not venue_name:
            return "I’m missing the venue name for this event."

        venue = Venue.objects.filter(name__iexact=venue_name).first()
        if not venue:
            return (
                f"I couldn’t find a venue called '{venue_name}'. "
                "Please create that venue first or specify a different name."
            )

        # NOTE: here we assume start/end are already proper datetimes.
        # If your planner returns strings, parse them before saving.
        start = params.get("start")
        end = params.get("end") or start
        capacity = params.get("capacity")
        ticket_price = params.get("ticket_price")
        description = params.get("description", "")

        event = Event.objects.create(
            organizer=organizer,
            venue=venue,
            title=title,
            description=description,
            start_time=start,
            end_time=end,
            capacity=capacity,
            status=params.get("status", "DRAFT"),
            ticket_price=ticket_price,
        )

        return f"✅ Event '{event.title}' has been created (ID: {event.event_id})."

    if action == "delete_event":
        identifier = params.get("identifier")
        if not identifier:
            return "I didn’t receive an event identifier to delete."

        qs = Event.objects.filter(organizer=organizer)

        # Try ID first, then title
        event = None
        try:
            event = qs.get(pk=int(identifier))
        except (ValueError, Event.DoesNotExist):
            event = qs.filter(title__iexact=identifier).first()

        if not event:
            return (
                f"I couldn’t find an event matching '{identifier}' "
                "under your organizer account."
            )

        title = event.title
        event.delete()
        return f"🗑️ Event '{title}' has been deleted."

    if action == "cancel_booking":
        booking_id = params.get("booking_id")
        if not booking_id:
            return "I didn’t receive a booking id to cancel."

        try:
            booking = Booking.objects.get(pk=booking_id, event__organizer=organizer)
        except Booking.DoesNotExist:
            return "I couldn’t find that booking under your events."

        booking.status = "CANCELLED"
        booking.save()
        return f"✅ Booking {booking.booking_id} has been cancelled."

    # You can implement update_event / create_venue here later.
    return "I don’t yet know how to execute this type of action."
