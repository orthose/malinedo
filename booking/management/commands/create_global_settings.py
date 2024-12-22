import datetime
from django.core.management.base import BaseCommand

from booking.models import GlobalSetting


class Command(BaseCommand):
    """
    Initialise les paramètres globaux de l'application
    """

    def handle(self, *args, **options):
        GlobalSetting.set_year(datetime.date.today().year)
        GlobalSetting.set_week(datetime.date.today().isocalendar().week)
