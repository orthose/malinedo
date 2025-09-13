from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

from accounts.models import ClubRole
from booking.models import (
    WeeklySession,
    SessionRegistration,
)
from accounts.models import User


class Command(BaseCommand):
    """
    Création des groupes du club et ajout de leurs permissions
    Les groupes de niveau de nage ne sont pas créés automatiquement
    Ils doivent être créés depuis l'interface d'administration

    Ce script doit être exécuté une seule fois lors du déploiement
    """

    def handle(self, *args, **options):
        ### Permissions ###
        all_weekly_session = Permission.objects.filter(
            codename__in=[
                f"{permission}_{WeeklySession._meta.model_name}"
                for permission in ["add", "change", "delete", "view"]
            ]
        )

        all_session_registration = Permission.objects.filter(
            codename__in=[
                f"{permission}_{SessionRegistration._meta.model_name}"
                for permission in ["add", "change", "delete", "view"]
            ]
        )

        all_user = Permission.objects.filter(
            codename__in=[
                f"{permission}_{User._meta.model_name}"
                for permission in ["add", "change", "delete", "view"]
            ]
        )

        ### Bureau ###
        board_group, _ = Group.objects.get_or_create(name=ClubRole.BOARD)
        board_group.permissions.add(*all_weekly_session)
        board_group.permissions.add(*all_session_registration)
        board_group.permissions.add(*all_user)

        ### Entraîneur ###
        Group.objects.get_or_create(name=ClubRole.COACH)
