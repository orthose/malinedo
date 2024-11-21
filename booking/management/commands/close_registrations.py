import datetime
from django.core.management.base import BaseCommand

from booking.models import (
    WeeklySession,
    WeeklySessionHistory,
    SessionRegistration,
    SessionRegistrationHistory,
    GlobalSetting,
)


class Command(BaseCommand):
    """
    Ferme les inscriptions pour la semaine courante
    et ouvre les inscriptions pour la semaine suivante

    Sauvegarde dans l'historique les inscriptions et sessions
    de la semaine pour les statistiques

    Efface les annulations des inscriptions et des sessions
    Supprime les inscriptions supplémentaires

    Ce script doit être lancé une seule fois par semaine
    en fin de semaine
    """

    def handle(self, *args, **options):
        # TODO: Mettre le site en maintenance ?

        year = GlobalSetting.get_year()
        week = GlobalSetting.get_week()

        ### Historisation des sessions ###
        WeeklySessionHistory.objects.bulk_create(
            [session.to_history(year, week) for session in WeeklySession.objects.all()]
        )

        ### Historisation des inscriptions ###
        SessionRegistrationHistory.objects.bulk_create(
            [
                registration.to_history(year, week)
                # Création de l'historique des inscriptions dans l'ordre de création original
                for registration in SessionRegistration.objects.all().order_by("pk")
            ]
        )

        ### Réinitialisation des annulations pour les sessions ###
        WeeklySession.objects.update(is_cancelled=False)

        ### Suppression des inscriptions supplémentaires ###
        SessionRegistration.objects.filter(is_regular=False).delete()

        ### Réinitialisation des annulations pour les inscriptions régulières ###
        SessionRegistration.objects.update(is_cancelled=False)

        ### Ouverture des inscriptions pour la semaine suivante ###
        monday = datetime.datetime.strptime(f"{year}-{week}-1", "%Y-%W-%w")
        dt_next_monday = monday + datetime.timedelta(days=7)
        next_monday = dt_next_monday.isocalendar()
        GlobalSetting.set_year(next_monday.year)
        GlobalSetting.set_week(next_monday.week)
