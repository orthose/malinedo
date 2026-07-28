import datetime
from django.core.management.base import BaseCommand

from booking.models import GlobalState


class Command(BaseCommand):
    """
    Initialise les paramètres globaux de l'application
    """

    def handle(self, *args, **options):
        GlobalState.set_year(datetime.date.today().year)
        GlobalState.set_week(datetime.date.today().isocalendar().week)
