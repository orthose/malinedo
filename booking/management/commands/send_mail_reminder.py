from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

from accounts.models import User
from booking.models import SessionRegistration, GlobalSetting


class Command(BaseCommand):
    """
    Envoi à chaque nageur un mail de rappel de ses entraînements de la semaine.
    """

    def handle(self, *args, **options):
        context = {
            "week": GlobalSetting.get_week(),
            "year": GlobalSetting.get_year(),
            "home_url": f"{settings.SITE_URL}{reverse('home')}",
            "settings_url": f"{settings.SITE_URL}{reverse('user_settings')}",
        }

        for user in User.objects.all():
            if not user.enable_notifications:
                continue

            context["user"] = user

            registrations = SessionRegistration.objects.filter(
                swimmer=user, is_cancelled=False, session__is_cancelled=False
            ).order_by("session__weekday", "session__start_hour")

            if registrations.count() > 0:
                swimmer_registrations = registrations.filter(swimmer_is_coach=False)
                coach_registrations = registrations.filter(swimmer_is_coach=True)

                context["swimmer_registrations"] = swimmer_registrations
                context["coach_registrations"] = coach_registrations

                message = render_to_string(
                    "booking/emails/reminder_sessions.txt", context
                )
                send_mail(
                    subject="[MaLineDo] Rappel de vos entraînements",
                    message=message,
                    from_email=None,
                    recipient_list=[user.email],
                )
