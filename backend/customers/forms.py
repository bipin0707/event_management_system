# backend/customers/forms.py

from django import forms
from .models import Customer


class AdminCustomerForm(forms.ModelForm):
    """
    Admin-facing form to manage customers from the custom admin portal.
    We keep a single 'name' field (matches ERD) plus the new profile fields.
    """

    class Meta:
        model = Customer
        fields = [
            "name",
            "email",
            "phone",
            "dob",
            "address",
            "city",
            "state",
            "zipcode",
            "country",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Full name"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "name@example.com"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Optional phone"}
            ),
            "dob": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
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
                attrs={"class": "form-control", "placeholder": "ZIP / Postal code"}
            ),
            "country": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Country"}
            ),
        }
