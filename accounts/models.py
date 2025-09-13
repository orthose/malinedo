from django.db import models
from django.contrib.auth.models import AbstractUser


class ClubRole:
    """
    Les différents rôles de l'application

    Les membres du bureau peuvent accéder à l'interface d'administration.
    Ce rôle est géré via un groupe Django afin de restreindre l'accès
    aux tables via des permissions. Il est créé avec le script create_club_groups.

    Les entraîneurs peuvent s'inscrire en tant qu'entraîneur à une séance.
    Ce rôle est géré via SessionGroup. Il est créé avec le script create_club_groups.

    Les nageurs appartiennent à des groupes de niveau de nage
    et peuvent s'inscrire aux séances correspondant à ces groupes.
    Ce rôle est géré via des groupes ajoutés dynamiquement dans SessionGroup.
    Par exemple : Loisir, Jeune, Compétition, etc.
    """

    BOARD = "Bureau"
    COACH = "Entraîneur"
    SWIMMER = "Nageur"


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
        return self.groups.filter(name=ClubRole.BOARD).exists()

    @property
    def is_coach(self) -> bool:
        return self.groups.filter(name=ClubRole.COACH).exists()

    def get_pk_groups(self) -> list[int]:
        return [group.pk for group in self.groups.all()]
