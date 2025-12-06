from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views

from . import views  # home view
from accounts import views as accounts_views  # our register view

urlpatterns = [
    path("admin/", admin.site.urls),

    # Home page
    path("", views.home, name="home"),

    # Events & bookings
    path("events/", include(("events.urls", "events"), namespace="events")),
    path("bookings/", include(("bookings.urls", "bookings"), namespace="bookings")),

    # Chatbot
    path("chat/", views.chat_page, name="chat_page"),
    path("chat/api/", views.chat_api, name="chat_api"),

    # Auth
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html"
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Password reset flow
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html"
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    # Registration
    path("register/", accounts_views.register, name="register"),

    # Accounts app (profile, become_organizer, etc.)
    path("accounts/", include("accounts.urls", namespace="accounts")),
]
