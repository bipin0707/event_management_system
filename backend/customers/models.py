from django.db import models


class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    # Keep single name column per ERD, but we will build it from first+last in forms
    name = models.CharField(max_length=150)
    email = models.EmailField(max_length=254, unique=True)
    phone = models.CharField(max_length=50, blank=True, null=True)

    # New fields per professor requirement
    dob = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)   # street
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    zipcode = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "CUSTOMER"

    def __str__(self):
        return f"{self.name} ({self.email})"
