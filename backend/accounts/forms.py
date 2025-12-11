# backend/accounts/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Admin
from django.contrib.auth.hashers import make_password
class RegisterForm(UserCreationForm):
    # Core auth fields
    email = forms.EmailField(
        required=True,
        help_text="Required. Used for password reset and notifications.",
    )

    # New: personal identity fields
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="First name",
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Last name",
    )

    # New: contact + demographic fields (go into CUSTOMER)
    phone = forms.CharField(
        max_length=50,
        required=False,
        label="Phone number",
    )

    dob = forms.DateField(
        required=False,
        label="Date of birth",
        widget=forms.DateInput(
            attrs={
                "type": "date",
            }
        ),
        help_text="Optional, used for analytics and eligibility checks.",
    )

    address = forms.CharField(
        max_length=255,
        required=False,
        label="Street address",
    )
    city = forms.CharField(
        max_length=100,
        required=False,
        label="City",
    )
    state = forms.CharField(
        max_length=100,
        required=False,
        label="State",
    )
    zipcode = forms.CharField(
        max_length=20,
        required=False,
        label="Zip code",
    )
    country = forms.CharField(
        max_length=100,
        required=False,
        label="Country",
    )

    class Meta:
        model = User
        # Note: extra non-User fields are allowed here because they are
        # declared explicitly on the form class.
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
            "phone",
            "dob",
            "address",
            "city",
            "state",
            "zipcode",
            "country",
        )

    def save(self, commit=True):
        """
        Save the User instance and leave Customer creation to the view.

        - Copies first_name / last_name / email onto the User model.
        - Returns the User object so accounts.views.register can
          build the CUSTOMER record and link UserProfile.customer.
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]

        if commit:
            user.save()
        return user


class AdminForm(forms.ModelForm):
    """
    ModelForm for managing records in the ADMIN table.

    We expose a plain 'password' field and internally hash it
    into the password_hash column. On edit, password is optional.
    """

    password = forms.CharField(
        required=False,
        label="Password",
        widget=forms.PasswordInput,
        help_text=(
            "Set a password for this admin. "
            "Leave blank when editing to keep the current password."
        ),
    )

    class Meta:
        model = Admin
        fields = ["username", "email", "role"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On create (no instance.pk yet), make password required
        if self.instance.pk is None:
            self.fields["password"].required = True

    def save(self, commit=True):
        admin = super().save(commit=False)
        pwd = self.cleaned_data.get("password")

        # Only update password_hash if a new password is provided
        if pwd:
            admin.password_hash = make_password(pwd)

        if commit:
            admin.save()
        return admin