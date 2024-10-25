from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

from booking.models import (
    ClubGroups,
    WeeklySession,
    SessionRegistration,
)


class Command(BaseCommand):
    """
    Création des groupes du club et ajout de leurs permissions

    Ce script doit être exécuté une seule fois lors du déploiement
    """

    def handle(self, *args, **options):
        ### Permissions ###
        all_weekly_training_session = Permission.objects.filter(
            codename__in=[
                f"{permission}_{WeeklySession._meta.model_name}"
                for permission in ["add", "change", "delete", "view"]
            ]
        )

        view_weekly_training_session = Permission.objects.get(
            codename=f"view_{WeeklySession._meta.model_name}"
        )

        all_registration = Permission.objects.filter(
            codename__in=[
                f"{permission}_{SessionRegistration._meta.model_name}"
                for permission in ["add", "change", "delete", "view"]
            ]
        )

        register_coach_session = Permission.objects.get(
            codename="register_coach_session"
        )

        register_leisure_session = Permission.objects.get(
            codename="register_leisure_session"
        )

        register_compet_session = Permission.objects.get(
            codename="register_compet_session"
        )

        ### Bureau ###
        board_group, _ = Group.objects.get_or_create(name=ClubGroups.BOARD.value)
        board_group.permissions.add(*all_weekly_training_session)

        ### Entraîneur ###
        coach_group, _ = Group.objects.get_or_create(name=ClubGroups.COACH.value)
        coach_group.permissions.add(register_coach_session)

        ### Loisir ###
        leisure_group, _ = Group.objects.get_or_create(name=ClubGroups.LEISURE.value)
        leisure_group.permissions.add(view_weekly_training_session)
        leisure_group.permissions.add(*all_registration)
        leisure_group.permissions.add(register_leisure_session)

        ### Compétition ###
        compet_group, _ = Group.objects.get_or_create(name=ClubGroups.COMPET.value)
        compet_group.permissions.add(view_weekly_training_session)
        compet_group.permissions.add(*all_registration)
        compet_group.permissions.add(register_compet_session)
