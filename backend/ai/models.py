# backend/ai/models.py

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class PendingAIAction(models.Model):
    """
    Stores a single 'planned' action for a user that must be confirmed
    (e.g. create/update/delete event, create venue, cancel booking, etc.)
    """

    ACTION_CHOICES = [
        ("create_event", "Create event"),
        ("update_event", "Update event"),
        ("delete_event", "Delete event"),
        ("create_venue", "Create venue"),
        ("cancel_booking", "Cancel booking"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pending_ai_actions",
    )
    action_type = models.CharField(max_length=40, choices=ACTION_CHOICES)
    payload = models.JSONField()  # structured parameters for the action
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()

    @classmethod
    def create_for(cls, user, action_type: str, payload: dict, minutes: int = 5):
        """
        Helper to create a pending action that automatically expires in N minutes.
        """
        return cls.objects.create(
            user=user,
            action_type=action_type,
            payload=payload,
            expires_at=timezone.now() + timedelta(minutes=minutes),
        )

    def __str__(self) -> str:
        return f"{self.user} · {self.action_type} · {self.created_at:%Y-%m-%d %H:%M}"
