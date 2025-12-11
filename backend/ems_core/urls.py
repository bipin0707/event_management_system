# backend/ems_core/urls.py

from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views

from . import views  # home + chat views
from accounts import views as accounts_views  # register + custom admin views

urlpatterns = [
    # ─── Custom Admin Portal (no Django admin.site) ────────────────────────
    # /admin/ will just redirect to the admin login (or you can change it later)
    path("admin/", RedirectView.as_view(pattern_name="admin_login", permanent=False)),
    path("admin/login/", accounts_views.admin_login, name="admin_login"),
    path("admin/logout/", accounts_views.admin_logout, name="admin_logout"),
    path("admin/dashboard/", accounts_views.admin_dashboard, name="admin_dashboard"),
    
    path("admin/organizers/", accounts_views.admin_organizer_list, name="admin_organizers"),
    path(
        "admin/organizers/<int:organizer_id>/approve/",
        accounts_views.admin_organizer_approve,
        name="admin_organizer_approve",
    ),
    path(
        "admin/organizers/<int:organizer_id>/reject/",
        accounts_views.admin_organizer_reject,
        name="admin_organizer_reject",
    ),
    # Admin: events
    path("admin/events/", accounts_views.admin_event_list, name="admin_events"),
    path("admin/events/new/", accounts_views.admin_event_create, name="admin_event_create"),
    path("admin/events/<int:event_id>/edit/", accounts_views.admin_event_edit, name="admin_event_edit"),
    path("admin/events/<int:event_id>/delete/", accounts_views.admin_event_delete, name="admin_event_delete"),

    # Admin: venues
    path("admin/venues/", accounts_views.admin_venue_list, name="admin_venues"),
    path("admin/venues/new/", accounts_views.admin_venue_create, name="admin_venue_create"),
    path("admin/venues/<int:venue_id>/edit/", accounts_views.admin_venue_edit, name="admin_venue_edit"),
    path("admin/venues/<int:venue_id>/delete/", accounts_views.admin_venue_delete, name="admin_venue_delete"),
    # Admin: customers
    path("admin/customers/", accounts_views.admin_customer_list, name="admin_customers"),
    path("admin/customers/new/", accounts_views.admin_customer_create, name="admin_customer_create"),
    path("admin/customers/<int:customer_id>/edit/", accounts_views.admin_customer_edit, name="admin_customer_edit"),
    path("admin/customers/<int:customer_id>/delete/", accounts_views.admin_customer_delete, name="admin_customer_delete"),
    # Admin: bookings
    path("admin/bookings/", accounts_views.admin_booking_list, name="admin_bookings"),
    path("admin/bookings/new/", accounts_views.admin_booking_create, name="admin_booking_create"),
    path("admin/bookings/<int:booking_id>/edit/", accounts_views.admin_booking_edit, name="admin_booking_edit"),
    path("admin/bookings/<int:booking_id>/delete/", accounts_views.admin_booking_delete, name="admin_booking_delete"),

    # Admin: payments
    path("admin/payments/", accounts_views.admin_payment_list, name="admin_payments"),
    path("admin/payments/new/", accounts_views.admin_payment_create, name="admin_payment_create"),
    path("admin/payments/<int:payment_id>/edit/", accounts_views.admin_payment_edit, name="admin_payment_edit"),
    path("admin/payments/<int:payment_id>/delete/", accounts_views.admin_payment_delete, name="admin_payment_delete"),

    # Admin: manage Admin users
    path("admin/admins/", accounts_views.admin_admin_list, name="admin_admins"),
    path("admin/admins/new/", accounts_views.admin_admin_create, name="admin_admin_create"),
    path("admin/admins/<int:admin_id>/edit/", accounts_views.admin_admin_edit, name="admin_admin_edit"),
    path("admin/admins/<int:admin_id>/delete/", accounts_views.admin_admin_delete, name="admin_admin_delete"),


    # Home page
    path("", views.home, name="home"),

    # Events & bookings
    path("events/", include(("events.urls", "events"), namespace="events")),
    path("bookings/", include(("bookings.urls", "bookings"), namespace="bookings")),

    # Chatbot
    path("chat/", views.chat_page, name="chat_page"),
    path("chat/api/", views.chat_api, name="chat_api"),

    # Auth (normal user login/logout)
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
