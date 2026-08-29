import datetime
from django.db import transaction
from django.core.management.base import BaseCommand

from booking.models import (
    WeeklySession,
    SessionRegistration,
    GlobalState,
)


class Command(BaseCommand):
    """
    Ferme les inscriptions pour la semaine courante
    et ouvre les inscriptions pour la semaine suivante

    Ce script doit être lancé une seule fois par semaine
    en fin de semaine
    """

    @transaction.atomic
    def handle(self, *args, **options):
        ### Semaine courante ###
        current_year = GlobalState.get_year()
        current_week = GlobalState.get_week()

        ### Semaine prochaine ###
        monday = datetime.datetime.fromisocalendar(current_year, current_week, 1)
        dt_next_monday = monday + datetime.timedelta(days=7)
        next_monday = dt_next_monday.isocalendar()
        new_year = next_monday.year
        new_week = next_monday.week
        GlobalState.set_year(new_year)
        GlobalState.set_week(new_week)

        ### Création des séances et récupération des inscriptions à créer pour la semaine prochaine ###
        current_sessions = WeeklySession.objects.filter(
            year=current_year, week=current_week
        )
        new_registrations = []

        for current_session in current_sessions:
            # Si la séance existe déjà dans le futur on la garde
            # On crée directement la séance sans utiliser bulk_create
            # car il faut que la séance existe pour créer une inscription associée
            # Par ailleurs il y a généralement peu de séances à créer
            # mais beaucoup plus d'inscriptions à créer
            new_session, _ = WeeklySession.objects.get_or_create(
                year=new_year,
                week=new_week,
                group=current_session.group,
                weekday=current_session.weekday,
                start_hour=current_session.start_hour,
                defaults={
                    "stop_hour": current_session.stop_hour,
                    "capacity": current_session.capacity,
                    # On réinitialise l'annulation de la séance
                    "is_cancelled": False,
                },
            )

            new_registrations.extend(
                SessionRegistration(
                    swimmer=registration.swimmer,
                    session=new_session,
                    swimmer_is_coach=registration.swimmer_is_coach,
                    is_regular=True,
                    # On réinitialise l'annulation de l'inscription
                    is_cancelled=False,
                )
                for registration in SessionRegistration.objects.filter(
                    session=current_session,
                    # On ne reporte dans le futur que les inscriptions régulières
                    is_regular=True,
                )
            )

        ### Création des inscriptions pour la semaine prochaine ###
        SessionRegistration.objects.bulk_create(
            new_registrations,
            # Si l'inscription existe déjà dans le futur on la garde
            ignore_conflicts=True,
        )

        # L'historisation des séances et inscriptions ne nécessite aucune opération supplémentaire
        # L'ancienne semaine courante est désormais considérée comme une semaine passée
