from django import forms


class BaseBookingForm(forms.Form):
    name = forms.CharField(max_length=120, label="Your name")
    email = forms.EmailField(max_length=150, label="Email")
    phone = forms.CharField(max_length=20, label="Phone (optional)", required=False)
    ticket_qty = forms.IntegerField(min_value=1, max_value=10, label="Number of tickets")


class ConferenceBookingForm(BaseBookingForm):
    # free booking, no extra fields
    pass


class PaidBookingForm(BaseBookingForm):
    PAYMENT_METHOD_CHOICES = [
        ("CASH", "Cash"),
        ("CARD", "Card"),
        ("ONLINE", "Online"),
    ]

    method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES, label="Payment method")
    card_details = forms.CharField(
        max_length=100,
        required=False,
        label="Card details (if paying by card)",
    )
