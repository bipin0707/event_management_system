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
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    ticket_qty = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="PENDING")
    booked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "BOOKING"

    def __str__(self):
        return f"Booking #{self.booking_id} for {self.event}"


#Payment Table


class Payment(models.Model):
    """
    Payment details for BOOKINGS.

    Per your updated requirements, payment for ticketed events is done only via
    credit or debit card. We drop the old CASH/CARD/ONLINE values and keep:
    - CREDIT
    - DEBIT
    """

    METHOD_CHOICES = [
        ("CREDIT", "Credit card"),
        ("DEBIT", "Debit card"),
    ]

    payment_id = models.AutoField(primary_key=True)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
    )
    # e.g. "Visa •••• 4242 | Day: 2025-12-20"
    card_details = models.CharField(max_length=100, null=True, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "PAYMENT"

    def __str__(self):
        return f"Payment #{self.payment_id} - {self.get_method_display()} - ${self.amount}"


