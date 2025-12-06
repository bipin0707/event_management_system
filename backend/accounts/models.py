from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from events.models import Organizer
from customers.models import Customer


class Admin(models.Model):
    ROLE_CHOICES = [
        ("ADMIN", "Admin"),
        ("STAFF", "Staff"),
    ]

    admin_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=60, unique=True)
    email = models.EmailField(max_length=150, unique=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    class Meta:
        db_table = "ADMIN"

    def __str__(self):
        return f"{self.username} ({self.role})"
    

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organizer = models.OneToOneField(
        Organizer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Linked organizer record if this user is an organizer.",
    )
    
    customer = models.OneToOneField(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_profile",
    )

    def is_organizer(self):
        return self.organizer is not None

    def __str__(self):
        return self.user.username


# --- signals: auto-create a profile for each user ---------------------------

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Just ensure profile exists (in case of superuser created via CLI)
    UserProfile.objects.get_or_create(user=instance)




