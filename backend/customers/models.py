from django.db import models

# Create your models here.
class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=120)
    email = models.EmailField(max_length=150, unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = "CUSTOMER"

    def __str__(self):
        return f"{self.name} ({self.email})"