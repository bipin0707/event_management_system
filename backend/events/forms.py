from django import forms
from django.utils import timezone

from .models import Event, Venue


class EventForm(forms.ModelForm):
    """
    Generic event form used on the organizer dashboard (create/edit).
    """

    class Meta:
        model = Event
        fields = [
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
                attrs={"class": "form-control", "min": 0}
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


# If you already referenced these elsewhere, keep them as thin wrappers
class OrganizerEventForm(EventForm):
    """
    Alias/thin subclass of EventForm, in case older code still imports it.
    """
    class Meta(EventForm.Meta):
        pass


class OrganizerVenueForm(forms.ModelForm):
    """
    Simple venue form for organizers to create/edit venues from the UI.
    """

    class Meta:
        model = Venue
        fields = ["name", "address", "capacity", "type"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Venue name"}
            ),
            "address": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Address"}
            ),
            "capacity": forms.NumberInput(
                attrs={"class": "form-control", "min": 0}
            ),
            "type": forms.Select(attrs={"class": "form-select"}),
        }
