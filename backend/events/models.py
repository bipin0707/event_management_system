from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


# Organizer Table (unchanged except for status/created_at we added earlier)
class Organizer(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    organizer_id = models.AutoField(primary_key=True)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="organizer_profile",
        help_text="Optional link to a login account for this organizer.",
    )

    name = models.CharField(max_length=120)
    email = models.EmailField(max_length=150, unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="PENDING",
        help_text="Organizer must be APPROVED by an admin before managing events.",
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "ORGANIZER"

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


# Venue Table
class Venue(models.Model):
    venue_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=120)

    # Address fields (venue-level, NOT event type anymore)
    address = models.CharField(max_length=255)  # street
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    zipcode = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)

    capacity = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(50000)]
    )

    class Meta:
        db_table = "VENUE"

    def __str__(self):
        return self.name


# Event Table
class Event(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("PUBLISHED", "Published"),
        ("CANCELLED", "Cancelled"),
    ]

    EVENT_TYPE_CHOICES = [
        ("EXHIBITION", "Exhibition"),
        ("CONFERENCE", "Conference"),
        ("CONCERT", "Concert"),
        ("SPORTS", "Sports Game"),
    ]

    event_id = models.AutoField(primary_key=True)
    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.PROTECT,
        related_name="events",
    )
    venue = models.ForeignKey(
        Venue,
        on_delete=models.PROTECT,
        related_name="events",
    )

    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        default="EXHIBITION",
        help_text="Determines whether the event is free/paid and how bookings work.",
    )

    title = models.CharField(max_length=150)
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional detailed description of the event.",
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    # Capacity is event-specific now (can differ from venue capacity if needed)
    capacity = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(50000)],
        blank=True,
        null=True,
        help_text="Required for conferences and paid events. Ignored for exhibitions.",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    ticket_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Required for Concert and Sports events. "
            "Must be zero or blank for Conferences and Exhibitions."
        ),
    )

    def clean(self):
        """
        Enforce:
        - start_time is not in the past (using current LOCAL timezone)
        - end_time is strictly after start_time
        - type-specific rules for capacity and ticket_price
        """
        super().clean()

        errors = {}

        # Datetime checks
        if self.start_time and self.end_time:
            now_local = timezone.localtime(timezone.now())
            start_local = timezone.localtime(self.start_time)
            end_local = timezone.localtime(self.end_time)

            if start_local < now_local:
                errors["start_time"] = "Start time cannot be in the past."

            if end_local <= start_local:
                errors["end_time"] = "End time must be after the start time."

        # Type-specific rules
        if self.event_type == "EXHIBITION":
            # No capacity / no price required
            if self.ticket_price not in (None, 0):
                errors["ticket_price"] = "Exhibitions must not have a ticket price."
        elif self.event_type == "CONFERENCE":
            # Must be free, but capacity is required
            if not self.capacity:
                errors["capacity"] = "Capacity is required for conferences."
            if self.ticket_price not in (None, 0) and self.ticket_price != 0:
                errors["ticket_price"] = "Conferences must be free (ticket price 0)."
        elif self.event_type in ("CONCERT", "SPORTS"):
            # Paid events: capacity + positive ticket price are required
            if not self.capacity:
                errors["capacity"] = "Capacity is required for paid events."
            if self.ticket_price is None or self.ticket_price <= 0:
                errors["ticket_price"] = "Ticket price must be greater than 0 for paid events."

        if errors:
            raise ValidationError(errors)

    class Meta:
        db_table = "EVENT"

    def __str__(self):
        return f"{self.title} @ {self.venue.name}"
