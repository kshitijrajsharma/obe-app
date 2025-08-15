from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email_notifications = models.BooleanField(
        default=True, help_text="Receive email notifications when exports are complete"
    )

    def __str__(self):
        return self.email or self.username
