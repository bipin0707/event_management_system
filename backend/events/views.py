from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from .models import Event, Venue, Organizer
from .forms import EventForm, OrganizerEventForm, OrganizerVenueForm
from accounts.models import UserProfile
from bookings.models import Booking, Payment


# ---------- Public event views ----------

def event_list(request):
    """
    Public page: list all published upcoming events.

    Only show events whose organizer is APPROVED.
    """
    now = timezone.now()
    events = (
        Event.objects
        .select_related("venue", "organizer")
        .filter(
            status="PUBLISHED",
            start_time__gte=now,
            organizer__status="APPROVED",   # 👈 only approved organizers
        )
        .order_by("start_time")
    )

    return render(
        request,
        "events/event_list.html",
        {"events": events},
    )


def event_detail(request, event_id):
    """
    Public page: detail view for a single event.
    """
    event = get_object_or_404(
        Event.objects.select_related("venue", "organizer"),
        pk=event_id,
    )

    return render(
        request,
        "events/event_detail.html",
        {"event": event},
    )


# ---------- Helpers to get organizer for current user ----------

def _get_profile_and_organizer(request):
    """
    Return (UserProfile or None, Organizer or None) for the logged-in user.
    Does NOT enforce any status; views can check organizer.status.
    """
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return None, None

    return profile, profile.organizer


def _get_user_organizer(request):
    """
    Backwards-compatible helper:
    returns the Organizer ONLY if it exists AND is APPROVED,
    otherwise returns None.
    """
    profile, organizer = _get_profile_and_organizer(request)
    if organizer and getattr(organizer, "status", None) == "APPROVED":
        return organizer
    return None


def _ensure_approved_organizer(request, context_redirect_name="accounts:profile"):
    """
    Shared check used by organizer-only views.

    Returns:
        (organizer or None, redirect_response or None)

    - If user has NO organizer -> redirect to become_organizer.
    - If organizer exists but status != APPROVED -> redirect to profile (or given view)
      with a clear message.
    - If organizer is APPROVED -> (organizer, None)
    """
    profile, organizer = _get_profile_and_organizer(request)

    # Not an organizer at all: send to become_organizer flow
    if not organizer:
        messages.error(
            request,
            "Only organizers can access this section. "
            "Please submit the 'Become an organizer' form first."
        )
        return None, redirect("accounts:become_organizer")

    # Organizer exists but not approved
    status = getattr(organizer, "status", None)
    if status != "APPROVED":
        if status == "PENDING":
            messages.warning(
                request,
                "Your organizer account is pending admin approval. "
                "You will be able to manage events once it is approved."
            )
        elif status == "REJECTED":
            messages.error(
                request,
                "Your organizer request has been rejected. "
                "Please contact the administrator for more information."
            )
        else:
            messages.error(
                request,
                "Your organizer account is not approved. "
                "Please contact the administrator."
            )
        return None, redirect(context_redirect_name)

    # Approved organizer
    return organizer, None


# ---------- Organizer dashboard views ----------

@login_required
def manage_events(request):
    """
    Organizer dashboard home:
    - list events belonging to this organizer
    - small stats section in the template (count, upcoming, etc.)
    """
    organizer, redirect_response = _ensure_approved_organizer(request)
    if redirect_response:
        return redirect_response

    events = (
        Event.objects
        .filter(organizer=organizer)
        .select_related("venue")
        .order_by("start_time")
    )

    venues = (
        Venue.objects.filter(events__organizer=organizer)
        .distinct()
        .order_by("name")
    )

    now = timezone.now()
    total_events = events.count()
    upcoming_events = events.filter(start_time__gte=now, status="PUBLISHED").count()
    draft_events = events.filter(status="DRAFT").count()

    context = {
        "organizer": organizer,
        "events": events,
        "venues": venues,
        "total_events": total_events,
        "upcoming_events": upcoming_events,
        "draft_events": draft_events,
    }
    return render(request, "events/manage_events.html", context)


@login_required
def event_create(request):
    """
    Organizer: create a new event from the dashboard.
    """
    organizer, redirect_response = _ensure_approved_organizer(request)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = organizer
            event.save()
            messages.success(request, f"Event '{event.title}' created successfully.")
            return redirect("events:manage_events")
    else:
        form = EventForm()

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "mode": "create",
        },
    )


@login_required
def event_edit(request, event_id):
    """
    Organizer: edit an existing event they own.
    """
    organizer, redirect_response = _ensure_approved_organizer(request)
    if redirect_response:
        return redirect_response

    event = get_object_or_404(Event, pk=event_id)

    if event.organizer != organizer:
        messages.error(request, "You do not have permission to edit this event.")
        return redirect("events:manage_events")

    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f"Event '{event.title}' updated successfully.")
            return redirect("events:manage_events")
    else:
        form = EventForm(instance=event)

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "mode": "edit",
            "event": event,
        },
    )


@login_required
def venue_create(request):
    """
    Organizer: create a new venue from the dashboard.
    (We keep it simple: any APPROVED organizer can create venues.)
    """
    organizer, redirect_response = _ensure_approved_organizer(request)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = OrganizerVenueForm(request.POST)
        if form.is_valid():
            venue = form.save()
            messages.success(request, f"Venue '{venue.name}' created successfully.")
            # After creating a venue, send them to create an event using it
            return redirect("events:event_create")
    else:
        form = OrganizerVenueForm()

    return render(
        request,
        "events/venue_form.html",
        {"form": form},
    )


# ---------- Organizer analytics dashboard ----------

@login_required
def organizer_analytics(request):
    """
    Analytics dashboard for an organizer:
    - summary KPIs (bookings, tickets, revenue)
    - per-event breakdown
    - simple month-by-month trend for the last 6 months
    """
    organizer, redirect_response = _ensure_approved_organizer(request)
    if redirect_response:
        return redirect_response

    now = timezone.now()

    # Events owned by this organizer
    events_qs = Event.objects.filter(organizer=organizer)
    event_ids = list(events_qs.values_list("pk", flat=True))

    # All non-cancelled bookings for these events
    bookings_qs = (
        Booking.objects.filter(
            event_id__in=event_ids,
            status__in=["PENDING", "APPROVED"],
        )
        .select_related("event")
    )

    # Payments for these bookings (for revenue)
    payments_qs = Payment.objects.filter(booking__event_id__in=event_ids)

    # Summary metrics
    total_events = events_qs.count()
    upcoming_events = events_qs.filter(start_time__gte=now, status="PUBLISHED").count()
    total_bookings = bookings_qs.count()
    total_tickets = bookings_qs.aggregate(total=Sum("ticket_qty"))["total"] or 0
    total_revenue = payments_qs.aggregate(total=Sum("amount"))["total"] or 0

    # Per-event stats
    per_event = (
        bookings_qs.values("event__event_id", "event__title")
        .annotate(
            bookings=Count("booking_id"),
            tickets=Sum("ticket_qty"),
            revenue=Sum("total_price"),
        )
        .order_by("-tickets", "event__title")
    )

    # Month-by-month stats for the last 6 months
    six_months_ago = now - timedelta(days=180)
    monthly = (
        bookings_qs.filter(booked_at__gte=six_months_ago)
        .annotate(month=TruncMonth("booked_at"))
        .values("month")
        .annotate(
            bookings=Count("booking_id"),
            tickets=Sum("ticket_qty"),
            revenue=Sum("total_price"),
        )
        .order_by("month")
    )

    context = {
        "organizer": organizer,
        "total_events": total_events,
        "upcoming_events": upcoming_events,
        "total_bookings": total_bookings,
        "total_tickets": total_tickets,
        "total_revenue": total_revenue,
        "per_event": per_event,
        "monthly": monthly,
    }
    return render(request, "events/organizer_analytics.html", context)
