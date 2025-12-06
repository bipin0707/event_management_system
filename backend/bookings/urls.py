from django.urls import path
from . import views

app_name = "bookings"

urlpatterns = [
    path("book/<int:event_id>/", views.book_event, name="book_event"),
    path("organizer/", views.organizer_bookings, name="organizer_bookings"),
    path(
        "organizer/event/<int:event_id>/",
        views.organizer_event_bookings,
        name="organizer_event_bookings",
    ),
    path("my/", views.my_bookings, name="my_bookings"),
    path("<int:booking_id>/receipt/", views.booking_receipt, name="booking_receipt"),
    path("<int:booking_id>/cancel/", views.cancel_booking, name="cancel_booking"),
]
