# backend/accounts/views.py

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import UserProfile, Admin
from .forms import RegisterForm
from events.models import Organizer
from bookings.models import Booking
from events.models import Event, Venue           # ← add this
from events.forms import AdminEventForm, AdminVenueForm
from customers.models import Customer
from customers.forms import AdminCustomerForm
from .forms import AdminForm 
from django.db.models import ProtectedError

# ─────────────────────────────────────────────────────────────
# User registration / profile
# ─────────────────────────────────────────────────────────────

def register(request):
    """
    User registration:
    - Create Django auth User
    - Create/Update CUSTOMER row with full details
    - Link Customer to UserProfile.customer
    """
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            # 1) Create the User
            user = form.save()

            # 2) Build full name from first + last
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            full_name = f"{first_name} {last_name}".strip()

            # 3) Extract CUSTOMER-related fields
            email = form.cleaned_data["email"]
            phone = form.cleaned_data.get("phone")

            dob = form.cleaned_data.get("dob")
            address = form.cleaned_data.get("address")
            city = form.cleaned_data.get("city")
            state = form.cleaned_data.get("state")
            zipcode = form.cleaned_data.get("zipcode")
            country = form.cleaned_data.get("country")

            # 4) Create or update Customer (email is unique in CUSTOMER)
            customer, created = Customer.objects.get_or_create(
                email=email,
                defaults={
                    "name": full_name,
                    "phone": phone,
                    "dob": dob,
                    "address": address,
                    "city": city,
                    "state": state,
                    "zipcode": zipcode,
                    "country": country,
                },
            )

            if not created:
                # Keep customer data in sync
                customer.name = full_name
                customer.phone = phone
                customer.dob = dob
                customer.address = address
                customer.city = city
                customer.state = state
                customer.zipcode = zipcode
                customer.country = country
                customer.save()

            # 5) Link Customer to UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.customer = customer
            profile.save()

            messages.success(request, "Account created successfully. You can now log in.")
            return redirect("login")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})



@login_required
def profile(request):
    user = request.user
    profile = getattr(user, "userprofile", None)
    customer = None
    if profile and profile.customer:
        # preferred: via UserProfile link
        customer = profile.customer
    else:
        # fallback: try to find by email (for older data)
        try:
            customer = Customer.objects.get(email=user.email)
        except Customer.DoesNotExist:
            customer = None
    bookings = (
        Booking.objects
        .select_related("event", "customer")
        .filter(customer__email=user.email)
        .order_by("-booked_at")
    )

    now = timezone.now()
    upcoming = [b for b in bookings if b.event.start_time >= now]
    past = [b for b in bookings if b.event.start_time < now]

    context = {
        "user": user,
        "profile": profile,
        "customer": customer,
        "upcoming_bookings": upcoming,
        "past_bookings": past,
        "now": now,
    }
    return render(request, "accounts/profile.html", context)


# ─────────────────────────────────────────────────────────────
# Become organizer flow (with admin approval)
# ─────────────────────────────────────────────────────────────

@login_required
def become_organizer(request):
    """
    Let a normal user request organizer status.

    - If they already have an APPROVED organizer linked, redirect to manage events.
    - If they have a PENDING organizer, show read-only info + message.
    - Otherwise, allow them to submit a new request, which will be PENDING
      until an admin approves it.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    existing_org = Organizer.objects.filter(user=request.user).order_by("-organizer_id").first()

    # Already approved: ensure profile link and send to dashboard
    if existing_org and existing_org.status == "APPROVED":
        if profile.organizer_id != existing_org.pk:
            profile.organizer = existing_org
            profile.save()
        messages.info(request, "You are already an approved organizer.")
        return redirect("events:manage_events")

    # Pending request: show waiting message
    if existing_org and existing_org.status == "PENDING":
        return render(
            request,
            "accounts/become_organizer.html",
            {
                "pending": True,
                "organizer": existing_org,
            },
        )

    # Rejected or no organizer: allow (re)submission
    if request.method == "POST":
        name = request.POST.get("name") or request.user.get_full_name() or request.user.username
        email = request.POST.get("email") or request.user.email
        phone = request.POST.get("phone")

        if not name or not email:
            messages.error(request, "Name and email are required.")
            return render(request, "accounts/become_organizer.html")

        # Do not allow another organizer with same email for a DIFFERENT user
        if Organizer.objects.exclude(user=request.user).filter(email=email).exists():
            messages.error(
                request,
                "An organizer with this email already exists. "
                "Please use a different email or contact the admin."
            )
            return render(
                request,
                "accounts/become_organizer.html",
                {"prefill_name": name, "prefill_email": email, "prefill_phone": phone},
            )

        organizer = Organizer.objects.create(
            user=request.user,
            name=name,
            email=email,
            phone=phone,
            status="PENDING",
        )

        messages.success(
            request,
            "Your request to become an organizer has been submitted. "
            "An admin must approve it before you can manage events."
        )
        return redirect("accounts:profile")

    # GET: blank form with sensible defaults
    return render(
        request,
        "accounts/become_organizer.html",
        {
            "prefill_name": request.user.get_full_name() or request.user.username,
            "prefill_email": request.user.email,
        },
    )


# ─────────────────────────────────────────────────────────────
# Custom Admin Portal (no Django admin.site)
# ─────────────────────────────────────────────────────────────

def admin_required(view_func):
    """
    Simple decorator that checks our own Admin session.
    Does NOT use django.contrib.auth permissions.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get("admin_id"):
            messages.error(request, "Admin login required.")
            return redirect("admin_login")
        return view_func(request, *args, **kwargs)

    return _wrapped


def admin_login(request):
    """
    Custom admin login based on the ADMIN table.
    Stores admin_id and role in the session.
    """
    if request.session.get("admin_id"):
        return redirect("admin_dashboard")

    error = None
    username_prefill = ""

    if request.method == "POST":
        from django.contrib.auth.hashers import check_password  # local import is fine too

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        username_prefill = username

        try:
            admin = Admin.objects.get(username=username)
        except Admin.DoesNotExist:
            admin = None

        if admin and check_password(password, admin.password_hash):
            request.session["admin_id"] = admin.admin_id
            request.session["admin_role"] = admin.role
            messages.success(request, f"Welcome, {admin.username}.")
            return redirect("admin_dashboard")
        else:
            error = "Invalid username or password."

    context = {
        "error": error,
        "username_prefill": username_prefill,
    }
    return render(request, "accounts/admin_login.html", context)


def admin_logout(request):
    request.session.pop("admin_id", None)
    request.session.pop("admin_role", None)
    messages.info(request, "You have been logged out of the admin portal.")
    return redirect("admin_login")


@admin_required
def admin_dashboard(request):
    """
    Overview cards: events, organizers, venues, customers, bookings, pending organizers.
    """
    from events.models import Event, Organizer, Venue
    from customers.models import Customer

    admin = Admin.objects.get(pk=request.session["admin_id"])

    stats = {
        "event_count": Event.objects.count(),
        "organizer_count": Organizer.objects.count(),
        "venue_count": Venue.objects.count(),
        "customer_count": Customer.objects.count(),
        "booking_count": Booking.objects.count(),
        "pending_organizers": Organizer.objects.filter(status="PENDING").count(),
        "admin_count": Admin.objects.count(),
    }
    
    admin_obj = Admin.objects.get(pk=request.session["admin_id"])

    context = {
        "admin": admin_obj,
        "stats": stats,
    }
    return render(request, "accounts/admin_dashboard.html", context)


# ─────────────────────────────────────────────────────────────
# Admin: Organizer management (approval / rejection)
# ─────────────────────────────────────────────────────────────

@admin_required
def admin_organizer_list(request):
    """
    List all organizers with status, and show approve/reject actions for PENDING ones.
    """
    status_filter = request.GET.get("status") or ""
    organizers = Organizer.objects.select_related("user").order_by("status", "name")

    if status_filter in ["PENDING", "APPROVED", "REJECTED"]:
        organizers = organizers.filter(status=status_filter)

    stats = {
        "pending": Organizer.objects.filter(status="PENDING").count(),
        "approved": Organizer.objects.filter(status="APPROVED").count(),
        "rejected": Organizer.objects.filter(status="REJECTED").count(),
    }

    context = {
        "organizers": organizers,
        "stats": stats,
        "status_filter": status_filter,
    }
    return render(request, "accounts/admin_organizers.html", context)


@admin_required
def admin_organizer_approve(request, organizer_id):
    organizer = get_object_or_404(Organizer, pk=organizer_id)
    organizer.status = "APPROVED"
    organizer.save()

    if organizer.user:
        profile, _ = UserProfile.objects.get_or_create(user=organizer.user)
        profile.organizer = organizer
        profile.save()

    messages.success(request, f"Organizer '{organizer.name}' has been approved.")
    return redirect("admin_organizers")


@admin_required
def admin_organizer_reject(request, organizer_id):
    organizer = get_object_or_404(Organizer, pk=organizer_id)
    organizer.status = "REJECTED"
    organizer.save()

    if organizer.user:
        profile, _ = UserProfile.objects.get_or_create(user=organizer.user)
        if profile.organizer_id == organizer.pk:
            profile.organizer = None
            profile.save()

    messages.info(request, f"Organizer '{organizer.name}' has been rejected.")
    return redirect("admin_organizers")

# ─────────────────────────────────────────────────────────────
# Admin: Event management (CRUD)
# ─────────────────────────────────────────────────────────────

@admin_required
def admin_event_list(request):
    events = (
        Event.objects
        .select_related("organizer", "venue")
        .order_by("-start_time")
    )
    return render(
        request,
        "events/admin_event_list.html",
        {"events": events},
    )


@admin_required
def admin_event_create(request):
    if request.method == "POST":
        form = AdminEventForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Event created successfully.")
            return redirect("admin_events")
    else:
        form = AdminEventForm()

    return render(
        request,
        "events/admin_event_form.html",
        {"form": form, "mode": "create"},
    )


@admin_required
def admin_event_edit(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    if request.method == "POST":
        form = AdminEventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Event updated successfully.")
            return redirect("admin_events")
    else:
        form = AdminEventForm(instance=event)

    return render(
        request,
        "events/admin_event_form.html",
        {"form": form, "mode": "edit", "event": event},
    )


@admin_required
def admin_event_delete(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    if request.method == "POST":
        title = event.title
        try:
            # this may raise ProtectedError if there are related bookings
            event.delete()
            messages.success(request, f"Event '{title}' has been deleted.")
        except ProtectedError:
            messages.error(
                request,
                (
                    f"Cannot delete event '{title}' because there are bookings "
                    "linked to it. Cancel or delete those bookings first."
                ),
            )
        # always go back to the Events list
        return redirect("admin_events")

    # GET: show confirmation page
    return render(
        request,
        "events/admin_event_confirm_delete.html",
        {"event": event},
    )



# ─────────────────────────────────────────────────────────────
# Admin: Venue management (CRUD)
# ─────────────────────────────────────────────────────────────

@admin_required
def admin_venue_list(request):
    venues = Venue.objects.order_by("name")
    return render(
        request,
        "events/admin_venue_list.html",   # ← LIST template
        {"venues": venues},
    )


@admin_required
def admin_venue_create(request):
    if request.method == "POST":
        form = AdminVenueForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Venue created successfully.")
            return redirect("admin_venues")
    else:
        form = AdminVenueForm()

    return render(
        request,
        "events/admin_venue_form.html",
        {"form": form, "mode": "create"},
    )


@admin_required
def admin_venue_edit(request, venue_id):
    venue = get_object_or_404(Venue, pk=venue_id)

    if request.method == "POST":
        form = AdminVenueForm(request.POST, instance=venue)
        if form.is_valid():
            form.save()
            messages.success(request, "Venue updated successfully.")
            return redirect("admin_venues")
    else:
        form = AdminVenueForm(instance=venue)

    return render(
        request,
        "events/admin_venue_form.html",
        {"form": form, "mode": "edit", "venue": venue},
    )


@admin_required
def admin_venue_delete(request, venue_id):
    venue = get_object_or_404(Venue, pk=venue_id)

    if request.method == "POST":
        name = venue.name
        try:
            venue.delete()
            messages.success(request, f"Venue '{name}' has been deleted.")
        except ProtectedError:
            messages.error(
                request,
                (
                    f"Cannot delete venue '{name}' because there are events "
                    "assigned to it. Reassign or delete those events first."
                ),
            )
        return redirect("admin_venues")

    return render(
        request,
        "events/admin_venue_confirm_delete.html",
        {"venue": venue},
    )

# ─────────────────────────────────────────────────────────────
# Admin: Customer management (CRUD)
# ─────────────────────────────────────────────────────────────

@admin_required
def admin_customer_list(request):
    customers = Customer.objects.order_by("name", "email")
    return render(
        request,
        "customers/admin_customer_list.html",
        {"customers": customers},
    )


@admin_required
def admin_customer_create(request):
    if request.method == "POST":
        form = AdminCustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer created successfully.")
            return redirect("admin_customers")
    else:
        form = AdminCustomerForm()

    return render(
        request,
        "customers/admin_customer_form.html",
        {"form": form, "mode": "create"},
    )


@admin_required
def admin_customer_edit(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)

    if request.method == "POST":
        form = AdminCustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer updated successfully.")
            return redirect("admin_customers")
    else:
        form = AdminCustomerForm(instance=customer)

    return render(
        request,
        "customers/admin_customer_form.html",
        {"form": form, "mode": "edit", "customer": customer},
    )


@admin_required
def admin_customer_delete(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)

    if request.method == "POST":
        name = customer.name
        customer.delete()
        messages.success(request, f"Customer '{name}' has been deleted.")
        return redirect("admin_customers")

    return render(
        request,
        "customers/admin_customer_confirm_delete.html",
        {"customer": customer},
    )


from bookings.forms import AdminBookingForm, AdminPaymentForm
from bookings.models import Booking, Payment

# ─────────────────────────────────────────────────────────────
# Admin: Booking management (CRUD)
# ─────────────────────────────────────────────────────────────

@admin_required
def admin_booking_list(request):
    bookings = (
        Booking.objects
        .select_related("event", "customer")
        .order_by("-booked_at")
    )
    return render(
        request,
        "bookings/admin_booking_list.html",
        {"bookings": bookings},
    )


@admin_required
def admin_booking_create(request):
    if request.method == "POST":
        form = AdminBookingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Booking created successfully.")
            return redirect("admin_bookings")
    else:
        form = AdminBookingForm()

    return render(
        request,
        "bookings/admin_booking_form.html",
        {"form": form, "mode": "create"},
    )


@admin_required
def admin_booking_edit(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)

    if request.method == "POST":
        form = AdminBookingForm(request.POST, instance=booking)
        if form.is_valid():
            form.save()
            messages.success(request, "Booking updated successfully.")
            return redirect("admin_bookings")
    else:
        form = AdminBookingForm(instance=booking)

    return render(
        request,
        "bookings/admin_booking_form.html",
        {"form": form, "mode": "edit", "booking": booking},
    )


@admin_required
def admin_booking_delete(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)

    if request.method == "POST":
        label = f"{booking.event.title} for {booking.customer.name}"
        booking.delete()
        messages.success(request, f"Booking '{label}' has been deleted.")
        return redirect("admin_bookings")

    return render(
        request,
        "bookings/admin_booking_confirm_delete.html",
        {"booking": booking},
    )


# ─────────────────────────────────────────────────────────────
# Admin: Payment management (CRUD)
# ─────────────────────────────────────────────────────────────

@admin_required
def admin_payment_list(request):
    payments = (
        Payment.objects
        .select_related("booking", "customer")
        .order_by("-paid_at")
    )
    return render(
        request,
        "bookings/admin_payment_list.html",
        {"payments": payments},
    )


@admin_required
def admin_payment_create(request):
    if request.method == "POST":
        form = AdminPaymentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Payment created successfully.")
            return redirect("admin_payments")
    else:
        form = AdminPaymentForm()

    return render(
        request,
        "bookings/admin_payment_form.html",
        {"form": form, "mode": "create"},
    )


@admin_required
def admin_payment_edit(request, payment_id):
    payment = get_object_or_404(Payment, pk=payment_id)

    if request.method == "POST":
        form = AdminPaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, "Payment updated successfully.")
            return redirect("admin_payments")
    else:
        form = AdminPaymentForm(instance=payment)

    return render(
        request,
        "bookings/admin_payment_form.html",
        {"form": form, "mode": "edit", "payment": payment},
    )


@admin_required
def admin_payment_delete(request, payment_id):
    payment = get_object_or_404(Payment, pk=payment_id)

    if request.method == "POST":
        label = f"{payment.amount} for booking #{payment.booking_id}"
        payment.delete()
        messages.success(request, f"Payment '{label}' has been deleted.")
        return redirect("admin_payments")

    return render(
        request,
        "bookings/admin_payment_confirm_delete.html",
        {"payment": payment},
    )

def _current_admin(request):
    """
    Convenience helper to fetch the currently logged-in Admin row
    using the admin_id stored in the session.
    """
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return None
    try:
        return Admin.objects.get(pk=admin_id)
    except Admin.DoesNotExist:
        return None


def _require_super_admin(request):
    """
    Optional helper: only allow ADMIN.role == 'ADMIN' to manage admin users.
    If you want STAFF to also manage admins, you can relax this check.
    """
    admin = _current_admin(request)
    if not admin or admin.role != "ADMIN":
        messages.error(request, "Only Admin users with role 'ADMIN' can manage admin accounts.")
        return False
    return True


@admin_required
def admin_admin_list(request):
    """
    List all admin users from the ADMIN table.
    """
    if not _require_super_admin(request):
        return redirect("admin_dashboard")

    admins = Admin.objects.order_by("username")

    context = {
        "admins": admins,
    }
    return render(request, "accounts/admin_admin_list.html", context)


@admin_required
def admin_admin_create(request):
    """
    Create a new admin record (username, email, role, password).
    """
    if not _require_super_admin(request):
        return redirect("admin_dashboard")

    if request.method == "POST":
        form = AdminForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Admin user created successfully.")
            return redirect("admin_admins")
    else:
        form = AdminForm()

    return render(
        request,
        "accounts/admin_admin_form.html",
        {"form": form, "mode": "create"},
    )


@admin_required
def admin_admin_edit(request, admin_id):
    """
    Edit an existing admin user. Password is optional and only updated
    if a new one is provided.
    """
    if not _require_super_admin(request):
        return redirect("admin_dashboard")

    admin_obj = get_object_or_404(Admin, pk=admin_id)

    if request.method == "POST":
        form = AdminForm(request.POST, instance=admin_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Admin user updated successfully.")
            return redirect("admin_admins")
    else:
        form = AdminForm(instance=admin_obj)

    return render(
        request,
        "accounts/admin_admin_form.html",
        {"form": form, "mode": "edit", "admin_obj": admin_obj},
    )


@admin_required
def admin_admin_delete(request, admin_id):
    """
    Delete an admin user. Do not allow an admin to delete themselves.
    """
    if not _require_super_admin(request):
        return redirect("admin_dashboard")

    admin_obj = get_object_or_404(Admin, pk=admin_id)
    current_admin = _current_admin(request)

    if current_admin and current_admin.pk == admin_obj.pk:
        messages.error(request, "You cannot delete your own admin account.")
        return redirect("admin_admins")

    if request.method == "POST":
        username = admin_obj.username
        admin_obj.delete()
        messages.success(request, f"Admin user '{username}' has been deleted.")
        return redirect("admin_admins")

    return render(
        request,
        "accounts/admin_admin_confirm_delete.html",
        {"admin_obj": admin_obj},
    )