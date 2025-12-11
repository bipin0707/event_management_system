# backend/events/forms.py

from django import forms
from django.utils import timezone

from .models import Event, Venue


class EventForm(forms.ModelForm):
    """
    Generic event form used on the organizer dashboard (create/edit).
    Now includes event_type so organizers choose what kind of event this is.
    """

    class Meta:
        model = Event
        fields = [
            "event_type",   # <- NEW: event type belongs to Event, not Venue
            "venue",
            "title",
            "description",
            "start_time",
            "end_time",
            "capacity",
            "status",
            "ticket_price",
        ]
        widgets = {
            "event_type": forms.Select(attrs={"class": "form-select"}),
            "venue": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Event title"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe your event (optional)…",
                }
            ),
            "start_time": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
            "end_time": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
            "capacity": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "ticket_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
        }

    def clean(self):
        """
        Extra safety on top of the model.clean():
        - ensure start_time is not in the past (server time)
        - ensure end_time is after start_time
        """
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        now = timezone.now()

        if start_time and start_time < now:
            self.add_error("start_time", "Start time cannot be in the past.")

        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "End time must be after the start time.")

        return cleaned_data


class OrganizerEventForm(EventForm):
    """
    Alias/thin subclass of EventForm, kept for backward compatibility.
    """
    class Meta(EventForm.Meta):
        pass


class OrganizerVenueForm(forms.ModelForm):
    """
    Venue form for organizers to create/edit venues from the UI.
    Venue no longer stores event type; only address and capacity.
    """

    class Meta:
        model = Venue
        fields = [
            "name",
            "address",
            "city",
            "state",
            "zipcode",
            "country",
            "capacity",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Venue name"}
            ),
            "address": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Street address"}
            ),
            "city": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "City"}
            ),
            "state": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "State"}
            ),
            "zipcode": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Zip code"}
            ),
            "country": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Country"}
            ),
            "capacity": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
        }


# ─────────────────────────────────────────────────────────────
# Admin forms (used only in the custom admin portal)
# ─────────────────────────────────────────────────────────────

class AdminEventForm(forms.ModelForm):
    """
    Admin-facing event form.

    Admin can choose organizer as well as venue and event_type.
    """

    class Meta:
        model = Event
        fields = [
            "organizer",
            "event_type",
            "venue",
            "title",
            "description",
            "start_time",
            "end_time",
            "capacity",
            "status",
            "ticket_price",
        ]
        widgets = {
            "organizer": forms.Select(attrs={"class": "form-select"}),
            "event_type": forms.Select(attrs={"class": "form-select"}),
            "venue": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Event title"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe the event (optional)…",
                }
            ),
            "start_time": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "end_time": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "capacity": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "ticket_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
        }

    def clean(self):
        """
        Reuse the same validation rules as EventForm.
        """
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        now = timezone.now()

        if start_time and start_time < now:
            self.add_error("start_time", "Start time cannot be in the past.")

        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "End time must be after the start time.")

        return cleaned_data


class AdminVenueForm(forms.ModelForm):
    """
    Admin-facing venue form. Fields match the new Venue schema.
    """

    class Meta:
        model = Venue
        fields = [
            "name",
            "address",
            "city",
            "state",
            "zipcode",
            "country",
            "capacity",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Venue name"}
            ),
            "address": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Street address"}
            ),
            "city": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "City"}
            ),
            "state": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "State"}
            ),
            "zipcode": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Zip code"}
            ),
            "country": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Country"}
            ),
            "capacity": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
        }
