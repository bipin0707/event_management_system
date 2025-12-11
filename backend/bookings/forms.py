# backend/bookings/forms.py

from django import forms
from .models import Booking, Payment


# ---------- Public booking forms (participants) -----------------------------

class BaseBookingForm(forms.Form):
    name = forms.CharField(max_length=120, label="First and last name")
    email = forms.EmailField(max_length=150, label="Email")
    phone = forms.CharField(max_length=20, label="Phone (optional)", required=False)
    ticket_qty = forms.IntegerField(min_value=1, max_value=10, label="Number of tickets")


class ConferenceBookingForm(BaseBookingForm):
    """
    Free conference booking, capacity-limited, no payment.
    """
    pass


class PaidBookingForm(BaseBookingForm):
    """
    Paid events (Concert / Sports):
    - Ticketed events must be paid by credit/debit.
    - For multi-day concerts we will also show a session_date field
      whose choices are injected from the view.
    """

    PAYMENT_METHOD_CHOICES = [
        ("CREDIT", "Credit card"),
        ("DEBIT", "Debit card"),
    ]

    method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        label="Payment method",
    )

    card_details = forms.CharField(
        max_length=100,
        required=False,
        label="Card details",
        help_text="e.g., 'Visa •••• 4242'",
    )

    # Used only for multi-day concerts; choices are set in the view.
    session_date = forms.ChoiceField(
        required=False,
        choices=[],
        label="Which day will you attend?",
    )

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get("method")
        card_details = cleaned.get("card_details")

        # Require card details whenever a card method is chosen
        if method in ("CREDIT", "DEBIT") and not card_details:
            self.add_error("card_details", "Please enter card details for card payments.")
        return cleaned


# ---------- Admin ModelForms (custom admin portal) -------------------------

class AdminBookingForm(forms.ModelForm):
    """
    Admin CRUD over BOOKING rows.
    Admin can adjust ticket quantity, prices and status.
    """

    class Meta:
        model = Booking
        fields = [
            "event",
            "customer",
            "ticket_qty",
            "unit_price",
            "total_price",
            "status",
        ]
        widgets = {
            "event": forms.Select(attrs={"class": "form-select"}),
            "customer": forms.Select(attrs={"class": "form-select"}),
            "ticket_qty": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "unit_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
            "total_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "booked_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
        }


class AdminPaymentForm(forms.ModelForm):
    """
    Admin CRUD over PAYMENT rows.
    """

    class Meta:
        model = Payment
        fields = [
            "booking",
            "customer",
            "amount",
            "method",
            "card_details",
        ]
        widgets = {
            "booking": forms.Select(attrs={"class": "form-select"}),
            "customer": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
            "method": forms.Select(attrs={"class": "form-select"}),
            "card_details": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Masked card (optional)"}
            ),
            "paid_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
        }
