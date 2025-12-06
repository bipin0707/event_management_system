from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from customers.models import Customer
from events.models import Event

#Booking Table
class Booking(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("CANCELLED", "Cancelled"),
    ]

    booking_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(
        Event,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    ticket_qty = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES)
    booked_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "BOOKING"

    def __str__(self):
        return f"Booking {self.booking_id} for {self.event.title} by {self.customer.name}"


#Payment Table
class Payment(models.Model):
    METHOD_CHOICES = [
        ("CASH", "Cash"),
        ("CARD", "Card"),
        ("ONLINE", "Online"),
    ]

    payment_id = models.AutoField(primary_key=True)
    booking = models.ForeignKey(
        Booking,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    card_details = models.CharField(max_length=100, blank=True, null=True)
    paid_at = models.DateTimeField()

    class Meta:
        db_table = "PAYMENT"

    def __str__(self):
        return f"Payment {self.payment_id} - {self.amount} by {self.customer.name}"
