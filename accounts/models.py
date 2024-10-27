from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    username = models.EmailField("Adresse e-mail", unique=True, blank=False)
    first_name = models.CharField("Prénom", max_length=150, blank=False)
    last_name = models.CharField("Nom", max_length=150, blank=False)
