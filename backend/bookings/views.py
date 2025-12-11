# backend/bookings/views.py

from decimal import Decimal
from datetime import timedelta

from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import Booking, Payment
from .forms import ConferenceBookingForm, PaidBookingForm
from customers.models import Customer
from events.models import Event
from accounts.models import UserProfile
from django.db.models import Sum


@login_required
def book_event(request, event_id):
    """
    Booking flow for an event, driven by Event.event_type:

    - EXHIBITION:
        * announcement only, NO booking allowed.

    - CONFERENCE:
        * free booking, capacity-limited
        * no payment
        * exactly one ticket per customer per event

    - CONCERT / SPORTS:
        * paid booking
        * capacity-limited
        * payment by credit/debit card only
        * for multi-day concerts, user must select which day they attend
    """
    event = get_object_or_404(Event.objects.select_related("venue"), pk=event_id)
    event_type_code = event.event_type  # EXHIBITION / CONFERENCE / CONCERT / SPORTS
    event_type_label = event.get_event_type_display()

    # EXHIBITION: no booking allowed
    if event_type_code == "EXHIBITION":
        messages.error(
            request,
            "This exhibition is for announcement only and does not require bookings.",
        )
        return redirect("events:event_detail", event_id=event.event_id)

    # Determine form class and whether it's a paid event
    if event_type_code == "CONFERENCE":
        FormClass = ConferenceBookingForm
        is_paid_event = False
    else:
        # CONCERT or SPORTS => paid events
        FormClass = PaidBookingForm
        is_paid_event = event_type_code in ("CONCERT", "SPORTS")

    # Capacity calculation based on non-cancelled bookings
    booked_qty = (
        Booking.objects.filter(
            event=event,
            status__in=["PENDING", "APPROVED"],
        ).aggregate(total=Sum("ticket_qty"))["total"]
        or 0
    )
    remaining_capacity = None
    if event.capacity is not None:
        remaining_capacity = event.capacity - booked_qty

    # Multi-day Concert detection (booking by day)
    start_date = event.start_time.date()
    end_date = event.end_time.date()
    is_multi_day_concert = (
        event_type_code == "CONCERT"
        and end_date > start_date
    )

    def _apply_concert_date_choices(form_instance):
        """
        For multi-day concerts, populate the session_date choices and mark as required.
        Safe even if the field is missing.
        """
        if not isinstance(form_instance, PaidBookingForm):
            return

        # If the form doesn't have session_date for some reason, just exit.
        if "session_date" not in form_instance.fields:
            return

        if not is_multi_day_concert:
            # If not multi-day, remove the field from the form entirely
            form_instance.fields.pop("session_date", None)
            return

        # Build list of day options between start and end (inclusive)
        days = []
        current = start_date
        while current <= end_date:
            days.append(current)
            current = current + timedelta(days=1)

        choices = [
            (d.isoformat(), d.strftime("%b %d, %Y"))
            for d in days
        ]
        form_instance.fields["session_date"].choices = choices
        form_instance.fields["session_date"].required = True

    # ------------- HANDLE POST & GET ----------------------------------------
    if request.method == "POST":
        form = FormClass(request.POST)

        # Conferences: lock ticket_qty to 1 (logical + visual)
        if event_type_code == "CONFERENCE" and "ticket_qty" in form.fields:
            form.fields["ticket_qty"].initial = 1
            form.fields["ticket_qty"].widget.attrs["readonly"] = True

        _apply_concert_date_choices(form)

        if form.is_valid():
            name = form.cleaned_data["name"]
            form_email = form.cleaned_data["email"]
            user_email = request.user.email or form_email
            email = user_email
            phone = form.cleaned_data.get("phone") or ""

            # Conference: force ticket_qty = 1
            if event_type_code == "CONFERENCE":
                ticket_qty = 1
            else:
                ticket_qty = form.cleaned_data["ticket_qty"]

            # Capacity check
            if remaining_capacity is not None and ticket_qty > remaining_capacity:
                form.add_error(
                    "ticket_qty",
                    f"Only {remaining_capacity} tickets remaining. Please choose a smaller quantity.",
                )
            else:
                # Get or create customer
                customer, _ = Customer.objects.get_or_create(
                    email=email,
                    defaults={"name": name, "phone": phone},
                )
                # Keep customer name/phone reasonably in sync
                if customer.name != name or (phone and customer.phone != phone):
                    customer.name = name
                    if phone:
                        customer.phone = phone
                    customer.save()

                # Conference: one booking per customer per event
                if event_type_code == "CONFERENCE":
                    existing = Booking.objects.filter(
                        event=event,
                        customer=customer,
                        status__in=["PENDING", "APPROVED"],
                    ).exists()
                    if existing:
                        form.add_error(
                            None,
                            "You already have a reservation for this conference."
                        )
                        return render(
                            request,
                            "bookings/book_event.html",
                            {
                                "form": form,
                                "event": event,
                                "event_type": event_type_label,
                                "remaining_capacity": remaining_capacity,
                                "is_paid_event": is_paid_event,
                            },
                        )

                # ----- PRICE LOGIC -----
                if is_paid_event:
                    if event.ticket_price is None or event.ticket_price <= 0:
                        form.add_error(
                            None,
                            "This event does not have a valid ticket price set by the organizer.",
                        )
                        return render(
                            request,
                            "bookings/book_event.html",
                            {
                                "form": form,
                                "event": event,
                                "event_type": event_type_label,
                                "remaining_capacity": remaining_capacity,
                                "is_paid_event": is_paid_event,
                            },
                        )
                    unit_price = event.ticket_price
                    total_price = unit_price * Decimal(ticket_qty)
                else:
                    unit_price = Decimal("0.00")
                    total_price = Decimal("0.00")
                # ----- END PRICE LOGIC -----

                # Create booking
                booking = Booking.objects.create(
                    event=event,
                    customer=customer,
                    ticket_qty=ticket_qty,
                    unit_price=unit_price,
                    total_price=total_price,
                    status="APPROVED",
                    booked_at=timezone.now(),
                )

                # Payment record only for paid events
                if is_paid_event:
                    method = form.cleaned_data["method"]          # "CREDIT" or "DEBIT"
                    card_details = form.cleaned_data.get("card_details") or ""

                    # Multi-day concert: ensure session_date is chosen and append to card_details
                    if is_multi_day_concert and "session_date" in form.cleaned_data:
                        session_date_str = form.cleaned_data.get("session_date")
                        if not session_date_str:
                            form.add_error(
                                "session_date",
                                "Please select the day you will attend."
                            )
                            return render(
                                request,
                                "bookings/book_event.html",
                                {
                                    "form": form,
                                    "event": event,
                                    "event_type": event_type_label,
                                    "remaining_capacity": remaining_capacity,
                                    "is_paid_event": is_paid_event,
                                },
                            )

                        if card_details:
                            card_details = f"{card_details} | Day: {session_date_str}"
                        else:
                            card_details = f"Day: {session_date_str}"

                    Payment.objects.create(
                        booking=booking,
                        customer=customer,
                        amount=total_price,
                        method=method,
                        card_details=card_details,
                        paid_at=timezone.now(),
                    )

                messages.success(
                    request,
                    f"Booking successful for {event.title}! "
                    f"Tickets: {ticket_qty}, Total: ${total_price}",
                )
                return redirect(
                    "bookings:booking_receipt",
                    booking_id=booking.booking_id,
                )

    else:
        # GET
        form = FormClass()
        if event_type_code == "CONFERENCE" and "ticket_qty" in form.fields:
            form.fields["ticket_qty"].initial = 1
            form.fields["ticket_qty"].widget.attrs["readonly"] = True

        _apply_concert_date_choices(form)

    context = {
        "event": event,
        "event_type": event_type_label,
        "form": form,
        "remaining_capacity": remaining_capacity,
        "is_paid_event": is_paid_event,
    }
    return render(request, "bookings/book_event.html", context)


@login_required
def organizer_bookings(request):
    """
    Show all bookings for events that belong to the logged-in organizer.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if not profile.organizer:
        messages.error(request, "Only organizers can view bookings for events.")
        return redirect("accounts:become_organizer")

    bookings = (
        Booking.objects.filter(event__organizer=profile.organizer)
        .select_related("event", "customer")
        .order_by("-booked_at")
    )

    return render(
        request,
        "bookings/organizer_bookings.html",
        {"bookings": bookings, "selected_event": None},
    )


@login_required
def organizer_event_bookings(request, event_id):
    """
    Show bookings only for a specific event that belongs to the logged-in organizer.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if not profile.organizer:
        messages.error(request, "Only organizers can view bookings for events.")
        return redirect("accounts:become_organizer")

    event = get_object_or_404(Event, pk=event_id)

    if event.organizer != profile.organizer:
        messages.error(request, "You do not have permission to view bookings for this event.")
        return redirect("bookings:organizer_bookings")

    bookings = (
        Booking.objects.filter(event=event)
        .select_related("customer")
        .order_by("-booked_at")
    )

    return render(
        request,
        "bookings/organizer_bookings.html",
        {"bookings": bookings, "selected_event": event},
    )


@login_required
def my_bookings(request):
    """
    List bookings made by the currently logged-in user as a participant.

    We link user -> booking via Customer.email == request.user.email.
    """
    email = request.user.email
    bookings = (
        Booking.objects.filter(customer__email=email)
        .select_related("event", "customer")
        .order_by("-booked_at")
    )
    
    total_bookings = bookings.count()
    total_spent = (
        bookings.aggregate(total=Sum("total_price"))["total"] or Decimal("0.00")
    )


    return render(
        request,
        "bookings/my_bookings.html",
        {
            "bookings": bookings,
            "now": timezone.now(),  # for cancel button conditions in template
            "total_bookings": total_bookings,
            "total_spent": total_spent,
        },
    )


@login_required
def booking_receipt(request, booking_id):
    """
    Simple receipt view for one booking – can be printed by the user.
    """
    booking = get_object_or_404(
        Booking.objects.select_related("event", "customer"),
        pk=booking_id,
    )
    payment = (
        Payment.objects.filter(booking=booking)
        .order_by("-paid_at")
        .first()
    )

    return render(
        request,
        "bookings/booking_receipt.html",
        {"booking": booking, "payment": payment},
    )


@login_required
def cancel_booking(request, booking_id):
    """
    Allow a participant to cancel their own upcoming booking.
    """
    booking = get_object_or_404(
        Booking.objects.select_related("event", "customer"),
        pk=booking_id,
        customer__email=request.user.email,  # ensure they own this booking
    )

    # Prevent canceling events that already happened
    if booking.event.start_time <= timezone.now():
        messages.error(request, "You cannot cancel a booking for an event that has already happened.")
        return redirect("bookings:my_bookings")

    if request.method == "POST":
        booking.status = "CANCELLED"
        booking.save()

        messages.success(
            request,
            f"Your booking for '{booking.event.title}' has been cancelled."
        )
        return redirect("bookings:my_bookings")

    return render(
        request,
        "bookings/booking_cancel_confirm.html",
        {"booking": booking},
    )
