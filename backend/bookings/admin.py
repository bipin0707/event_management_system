from django.contrib import admin
from .models import Booking, Payment


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "booking_id",
        "event",
        "customer",
        "ticket_qty",
        "unit_price",
        "total_price",
        "status",
        "booked_at",
    )
    # Remove event__venue__type – that field no longer exists
    list_filter = ("status",)
    search_fields = ("event__title", "customer__name", "customer__email")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "payment_id",
        "booking",
        "customer",
        "amount",
        "method",
        "paid_at",
    )
    list_filter = ("method",)
    search_fields = ("customer__name", "customer__email", "booking__event__title")
