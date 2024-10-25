import datetime
from django.core.management.base import BaseCommand

from booking.models import WeeklySession


class Command(BaseCommand):
    """
    Initialise les sessions pour l'année 2024
    """

    def handle(self, *args, **options):
        ### Jeune ###
        WeeklySession.objects.update_or_create(
            group="J",
            weekday=2,
            start_hour=datetime.time(18, 30),
            stop_hour=datetime.time(20, 0),
            capacity=8,
        )
        WeeklySession.objects.update_or_create(
            group="J",
            weekday=3,
            start_hour=datetime.time(17, 0),
            stop_hour=datetime.time(18, 0),
            capacity=4,
        )

        ### Loisir ###
        WeeklySession.objects.update_or_create(
            group="L",
            weekday=2,
            start_hour=datetime.time(20, 30),
            stop_hour=datetime.time(21, 30),
            capacity=4,
        )
        WeeklySession.objects.update_or_create(
            group="L",
            weekday=3,
            start_hour=datetime.time(17, 0),
            stop_hour=datetime.time(18, 0),
            capacity=4,
        )
        WeeklySession.objects.update_or_create(
            group="L",
            weekday=3,
            start_hour=datetime.time(18, 0),
            stop_hour=datetime.time(19, 0),
            capacity=4,
        )
        WeeklySession.objects.update_or_create(
            group="L",
            weekday=4,
            start_hour=datetime.time(20, 30),
            stop_hour=datetime.time(21, 30),
            capacity=8,
        )
        WeeklySession.objects.update_or_create(
            group="L",
            weekday=5,
            start_hour=datetime.time(20, 30),
            stop_hour=datetime.time(21, 30),
            capacity=8,
        )

        ### Compétition ###
        WeeklySession.objects.update_or_create(
            group="C",
            weekday=1,
            start_hour=datetime.time(20, 0),
            stop_hour=datetime.time(21, 30),
            capacity=8,
        )
        WeeklySession.objects.update_or_create(
            group="C",
            weekday=2,
            start_hour=datetime.time(20, 0),
            stop_hour=datetime.time(21, 30),
            capacity=8,
        )
        WeeklySession.objects.update_or_create(
            group="C",
            weekday=4,
            start_hour=datetime.time(19, 30),
            stop_hour=datetime.time(20, 30),
            capacity=12,
        )
        WeeklySession.objects.update_or_create(
            group="C",
            weekday=4,
            start_hour=datetime.time(20, 30),
            stop_hour=datetime.time(21, 30),
            capacity=4,
        )
        WeeklySession.objects.update_or_create(
            group="C",
            weekday=5,
            start_hour=datetime.time(19, 0),
            stop_hour=datetime.time(20, 30),
            capacity=12,
        )
