from django.db import models
from django.contrib.auth.models import AbstractUser

from booking.groups import ClubGroup


class User(AbstractUser):
    # Authentification par email
    username = models.EmailField("Adresse e-mail", unique=True, blank=False)
    email = models.EmailField("Adresse e-mail", unique=True, blank=True)
    first_name = models.CharField("Prénom", max_length=150, blank=False)
    last_name = models.CharField("Nom", max_length=150, blank=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Forcer email = username
        self.email = self.username

    @property
    def is_board_member(self) -> bool:
        return self.groups.filter(name=ClubGroup.BOARD).exists()
