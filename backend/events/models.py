from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


# Organizer Table
class Organizer(models.Model):
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

    class Meta:
        db_table = "ORGANIZER"

    def __str__(self):
        return self.name


# Venue Table
class Venue(models.Model):
    VENUE_TYPE_CHOICES = [
        ("Exhibition", "Exhibition"),
        ("Conference", "Conference"),
        ("Concert", "Concert"),
        ("Sports", "Sports"),
    ]

    venue_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=200)
    capacity = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(50000)]
    )
    type = models.CharField(max_length=50, choices=VENUE_TYPE_CHOICES)

    class Meta:
        db_table = "VENUE"

    def __str__(self):
        return f"{self.name} ({self.type})"


# Event Table
class Event(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("PUBLISHED", "Published"),
        ("CANCELLED", "Cancelled"),
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
    title = models.CharField(max_length=150)
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional detailed description of the event.",
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    capacity = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(50000)],
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    ticket_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Required for Concert and Sports events. "
            "Leave blank for Conferences and Exhibitions."
        ),
    )

    def clean(self):
        """
        Enforce:
        - start_time is not in the past (using current LOCAL timezone)
        - end_time is strictly after start_time
        """
        super().clean()

        # If datetimes are missing (e.g. partially filled admin form), skip
        if not self.start_time or not self.end_time:
            return

        # Current local time according to Django's active timezone
        now_local = timezone.localtime(timezone.now())

        # Convert event times to the same local timezone
        start_local = timezone.localtime(self.start_time)
        end_local = timezone.localtime(self.end_time)

        errors = {}

        # Start time cannot be in the past
        if start_local < now_local:
            errors["start_time"] = "Start time cannot be in the past."

        # End time must be after start time
        if end_local <= start_local:
            errors["end_time"] = "End time must be after the start time."

        if errors:
            raise ValidationError(errors)

    class Meta:
        db_table = "EVENT"

    def __str__(self):
        return f"{self.title} @ {self.venue.name}"
