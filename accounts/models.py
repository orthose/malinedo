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
    enable_notifications = models.BooleanField(
        "Activer les notifications", default=True
    )

    def save(self, *args, **kwargs):
        # Forcer email = username puis sauvegarder
        self.email = self.username
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from booking.models import SessionRegistration, GlobalState

        # Utilisateur anonymisé
        deleted_user = self.__class__.objects.get_or_create(
            username=f"deleted-{self.pk}@malinedo.invalid",
            first_name="Inconnu",
            last_name=self.pk,
            enable_notifications=False,
        )[0]

        # Suppression des inscriptions des semaines en cours et futures
        current_year = GlobalState.get_year()
        current_week = GlobalState.get_week()
        SessionRegistration.objects.filter(swimmer=self).filter(
            models.Q(year__gt=current_year)
            | models.Q(year=current_year, week__gte=current_week)
        ).delete()

        # Anonymisation de l'historique des inscriptions
        SessionRegistration.objects.filter(swimmer=self).update(swimmer=deleted_user)

        return super().delete(*args, **kwargs)

    @property
    def is_board_member(self) -> bool:
        return self.groups.filter(name=ClubRole.BOARD).exists()

    @property
    def is_coach(self) -> bool:
        return self.groups.filter(name=ClubRole.COACH).exists()

    @property
    def max_registrations_per_week(self) -> int:
        from booking.models import SessionGroup

        max_registrations = [
            session_group.max_registrations_per_week
            for session_group in SessionGroup.objects.filter(
                groups__in=self.groups.all()
            )
        ]
        max_registrations.append(0)

        return max(max_registrations)
