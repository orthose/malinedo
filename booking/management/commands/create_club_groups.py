from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

from booking.models import (
    ClubGroup,
    RegisterPermission,
    WeeklySession,
    SessionRegistration,
)
from accounts.models import User


class Command(BaseCommand):
    """
    Création des groupes du club et ajout de leurs permissions

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

        register_coach_session = Permission.objects.get(
            codename=RegisterPermission.COACH
        )

        register_leisure_session = Permission.objects.get(
            codename=RegisterPermission.LEISURE
        )

        register_young_session = Permission.objects.get(
            codename=RegisterPermission.YOUNG
        )

        register_competn1_session = Permission.objects.get(
            codename=RegisterPermission.COMPET_N1
        )

        register_competn2_session = Permission.objects.get(
            codename=RegisterPermission.COMPET_N2
        )

        ### Bureau ###
        board_group, _ = Group.objects.get_or_create(name=ClubGroup.BOARD)
        board_group.permissions.add(*all_weekly_session)
        board_group.permissions.add(*all_session_registration)
        board_group.permissions.add(*all_user)

        ### Entraîneur ###
        coach_group, _ = Group.objects.get_or_create(name=ClubGroup.COACH)
        coach_group.permissions.add(register_coach_session)

        ### Loisir ###
        leisure_group, _ = Group.objects.get_or_create(name=ClubGroup.LEISURE)
        leisure_group.permissions.add(register_leisure_session)

        ### Jeune ###
        young_group, _ = Group.objects.get_or_create(name=ClubGroup.YOUNG)
        young_group.permissions.add(register_young_session)

        ### Compétition N1 ###
        compet_group, _ = Group.objects.get_or_create(name=ClubGroup.COMPET_N1)
        compet_group.permissions.add(register_competn1_session)

        ### Compétition N2 ###
        compet_group, _ = Group.objects.get_or_create(name=ClubGroup.COMPET_N2)
        compet_group.permissions.add(register_competn2_session)
