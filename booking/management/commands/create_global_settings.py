from django.core.management.base import BaseCommand

from booking.models import (
    GlobalSetting,
    get_current_year,
    get_current_week,
)


class Command(BaseCommand):
    """
    Initialise les paramètres globaux de l'application
    """

    def handle(self, *args, **options):
        GlobalSetting.set_year(get_current_year())
        GlobalSetting.set_week(get_current_week())
        GlobalSetting.set_is_booking_active(True)
