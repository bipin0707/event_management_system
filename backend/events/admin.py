from django.contrib import admin
from .models import Organizer, Venue, Event, Event


@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ("organizer_id", "name", "email", "phone")
    search_fields = ("name", "email")


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("venue_id", "name", "type", "capacity")
    list_filter = ("type",)
    search_fields = ("name", "address")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "venue", "organizer", "start_time", "status", "ticket_price")
    list_filter = ("status", "venue__type")
    search_fields = ("title", "venue__name", "organizer__name")

    fieldsets = (
        ("Basic info", {
            "fields": ("title", "description", "organizer", "venue")
        }),
        ("Schedule & Capacity", {
            "fields": ("start_time", "end_time", "capacity", "status")
        }),
        ("Pricing", {
            "fields": ("ticket_price",),
        }),
    )
