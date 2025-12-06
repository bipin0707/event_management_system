from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from .models import UserProfile
from events.models import Organizer
from django.contrib.auth.decorators import login_required


from bookings.models import Booking
from django.utils import timezone
from .forms import RegisterForm


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully. You can now log in.")
            from django.shortcuts import redirect
            return redirect("login")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})

@login_required
def become_organizer(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # Already organizer? Send to manage page
    if profile.organizer:
        messages.info(request, "You are already registered as an organizer.")
        return redirect("events:manage_events")

    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email") or request.user.email
        phone = request.POST.get("phone")

        if not name or not email:
            messages.error(request, "Name and email are required.")
            return render(request, "accounts/become_organizer.html")

        # ❗ New part: block duplicate organizer emails
        if Organizer.objects.filter(email=email).exists():
            messages.error(
                request,
                "An organizer with this email already exists. "
                "Please use a different email or contact the admin."
            )
            # keep the entered values visible in the form
            return render(request, "accounts/become_organizer.html", {
                "prefill_name": name,
                "prefill_email": email,
                "prefill_phone": phone,
            })

        # Safe to create a *new* organizer now
        organizer = Organizer.objects.create(
            name=name,
            email=email,
            phone=phone,
        )

        profile.organizer = organizer
        profile.save()

        messages.success(request, "You are now registered as an organizer.")
        return redirect("events:manage_events")

    return render(request, "accounts/become_organizer.html")

@login_required
def profile(request):
    user = request.user
    profile = getattr(user, "userprofile", None)

    # Bookings made by this user's email
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
        "upcoming_bookings": upcoming,
        "past_bookings": past,
        "now": now,  
    }
    return render(request, "accounts/profile.html", context)