# backend/bookings/views.py

from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import Booking, Payment
from .forms import ConferenceBookingForm, PaidBookingForm  # BaseBookingForm used inside these
from customers.models import Customer
from events.models import Event
from accounts.models import UserProfile


@login_required
def book_event(request, event_id):
    """
    Booking flow for an event.

    - Exhibition: no booking allowed.
    - Conference: free booking (ConferenceBookingForm).
    - Concert / Sports: paid booking (PaidBookingForm).
    - Capacity check based on existing non-cancelled bookings.
    - Customer is resolved by email; we prefer the logged-in user's email.
    - Payment row is created for paid events.
    - On success, redirect to a booking receipt page.
    """
    event = get_object_or_404(Event.objects.select_related("venue"), pk=event_id)
    event_type = event.venue.type if event.venue else None

    # Exhibition: no booking allowed
    if event_type == "Exhibition":
        messages.error(request, "This exhibition does not require bookings.")
        return redirect("events:event_detail", event_id=event.event_id)

    # Determine which form to use
    if event_type == "Conference":
        FormClass = ConferenceBookingForm
        is_paid_event = False
    else:  # Concert or Sports (paid events)
        FormClass = PaidBookingForm
        is_paid_event = True

    # Capacity validation: how many tickets already booked (non-cancelled)
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

    if request.method == "POST":
        form = FormClass(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            # Prefer the logged-in user's email for linkage to Customer/Booking
            form_email = form.cleaned_data["email"]
            user_email = request.user.email or form_email
            email = user_email
            phone = form.cleaned_data.get("phone") or ""
            ticket_qty = form.cleaned_data["ticket_qty"]

            # Capacity check
            if remaining_capacity is not None and ticket_qty > remaining_capacity:
                form.add_error(
                    "ticket_qty",
                    f"Only {remaining_capacity} tickets remaining. Please choose a smaller quantity.",
                )
            else:
                # Get or create customer based on email
                customer, _ = Customer.objects.get_or_create(
                    email=email,
                    defaults={"name": name, "phone": phone},
                )
                # Keep customer details reasonably up to date
                if customer.name != name or (phone and customer.phone != phone):
                    customer.name = name
                    if phone:
                        customer.phone = phone
                    customer.save()

                # ----- PRICE LOGIC -----
                if is_paid_event:
                    if event.ticket_price is None:
                        form.add_error(
                            None,
                            "This event does not have a ticket price set by the organizer.",
                        )
                        return render(
                            request,
                            "bookings/book_event.html",
                            {
                                "form": form,
                                "event": event,
                                "event_type": event_type,
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

                # Payment record
                method = "ONLINE"
                card_details = ""
                if is_paid_event:
                    method = form.cleaned_data["method"]
                    card_details = form.cleaned_data.get("card_details") or ""

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

                # Redirect to a simple receipt page (can be printed by the user)
                return redirect("bookings:booking_receipt", booking_id=booking.booking_id)

    else:
        form = FormClass()

    context = {
        "event": event,
        "event_type": event_type,
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

    We link user -> booking via Customer.email == request.user.email
    (consistent with the ERD, no extra field needed).
    """
    email = request.user.email
    bookings = (
        Booking.objects.filter(customer__email=email)
        .select_related("event", "customer")
        .order_by("-booked_at")
    )

    return render(
        request,
        "bookings/my_bookings.html",
        {
            "bookings": bookings,
            "now": timezone.now(),  # 👈 for cancel button conditions in template
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

    return render(request, "bookings/booking_cancel_confirm.html", {
        "booking": booking,
    })
