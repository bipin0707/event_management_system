from django.contrib import admin
from .models import Organizer, Venue, Event


@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ("organizer_id", "name", "email", "phone", "status")
    list_filter = ("status",)
    search_fields = ("name", "email")


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = (
        "venue_id",
        "name",
        "address",
        "city",
        "state",
        "capacity",
    )
    # No more "type" field – filter by city/state instead
    list_filter = ("city", "state")
    search_fields = ("name", "address", "city", "state", "country")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "event_type",     # ← new: event type on Event
        "venue",
        "organizer",
        "start_time",
        "status",
        "ticket_price",
    )
    # No more "venue__type" – filter by event_type instead
    list_filter = ("status", "event_type")
    search_fields = ("title", "venue__name", "organizer__name")

    fieldsets = (
        ("Basic info", {
            "fields": ("title", "description", "organizer", "venue", "event_type")
        }),
        ("Schedule & Capacity", {
            "fields": ("start_time", "end_time", "capacity", "status")
        }),
        ("Pricing", {
            "fields": ("ticket_price",),
        }),
    )
