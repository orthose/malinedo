import datetime
from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse
from django.db.models.query import QuerySet
from django.shortcuts import redirect, render
from django.urls import path
from django.utils.http import urlencode

from .models import (
    SessionGroup,
    WeeklySession,
    SessionRegistration,
    GlobalState,
)
from .forms import AdminCancelFutureSessionsForm


@admin.register(SessionGroup)
class SessionGroupAdmin(admin.ModelAdmin):
    list_filter = [
        "name",
        "groups",
    ]


@admin.register(WeeklySession)
class WeeklySessionAdmin(admin.ModelAdmin):
    ordering = [
        "year",
        "week",
        "weekday",
        "start_hour",
    ]
    list_filter = [
        "year",
        "week",
        "weekday",
        "group",
    ]
    search_fields = ["year", "week"]
    actions = ["lock_sessions", "unlock_sessions"]

    @admin.action(description="Annuler les sessions hebdomadaires sélectionnées")
    def lock_sessions(self, request: HttpRequest, queryset: QuerySet[WeeklySession]):
        queryset.update(is_cancelled=True)

    @admin.action(description="Restaurer les sessions hebdomadaires sélectionnées")
    def unlock_sessions(self, request: HttpRequest, queryset: QuerySet[WeeklySession]):
        queryset.update(is_cancelled=False)

    def changelist_view(self, request: HttpRequest, extra_context=None) -> HttpResponse:
        # Affichage des séances de la semaine courante par défaut
        if not request.GET:
            params = {
                "year": GlobalState.get_year(),
                "week": GlobalState.get_week(),
            }
            return redirect(f"{request.path}?{urlencode(params)}")
        return super().changelist_view(request, extra_context)

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet):
        """
        Permet d'appliquer la logique de suppression de WeeklySession.delete()
        """
        for obj in queryset:
            self.delete_model(request, obj)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "cancel-future-sessions/",
                self.admin_site.admin_view(self.cancel_future_sessions),
                name="cancel_future_sessions",
            ),
        ]
        return custom_urls + urls

    def cancel_future_sessions(self, request: HttpRequest) -> HttpResponse:
        if request.method == "POST":
            form = AdminCancelFutureSessionsForm(request.POST)
            if form.is_valid():
                start_date: datetime.date = form.cleaned_data["start_date"]
                stop_date: datetime.date = form.cleaned_data["stop_date"]

                count_cancelled_sessions = 0
                while start_date <= stop_date:
                    date = start_date.isocalendar()
                    (year, week, weekday) = (date.year, date.week, date.weekday)
                    start_date += datetime.timedelta(days=1)

                    for session in WeeklySession.objects.filter(
                        year=GlobalState.get_year(),
                        week=GlobalState.get_week(),
                        weekday=weekday,
                    ):
                        WeeklySession.objects.update_or_create(
                            year=year,
                            week=week,
                            weekday=weekday,
                            group=session.group,
                            start_hour=session.start_hour,
                            defaults={
                                "stop_hour": session.stop_hour,
                                "capacity": session.capacity,
                                "is_cancelled": True,
                            },
                        )
                        count_cancelled_sessions += 1

                if count_cancelled_sessions == 0:
                    self.message_user(
                        request, "Aucune séance annulée", messages.WARNING
                    )
                else:
                    self.message_user(
                        request,
                        f"Vous avez annulé avec succès {count_cancelled_sessions} séance(s)",
                        messages.SUCCESS,
                    )

                return redirect("admin:cancel_future_sessions")

        else:
            form = AdminCancelFutureSessionsForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "Annuler séances futures",
            "form": form,
        }

        return render(
            request,
            "admin/booking/weeklysession/cancel_future_sessions.html",
            context,
        )

    class Media:
        css = {
            "all": ("admin/weeklysession.css",),
        }


@admin.register(SessionRegistration)
class SessionRegistrationAdmin(admin.ModelAdmin):
    ordering = [
        "session__year",
        "session__week",
        "session__weekday",
        "session__start_hour",
        "pk",
    ]
    search_fields = [
        "swimmer__first_name",
        "swimmer__last_name",
        "session__year",
        "session__week",
    ]
    list_filter = [
        "session__year",
        "session__week",
        "session__weekday",
        "session__group",
        "is_regular",
        "is_cancelled",
        "swimmer_is_coach",
    ]
    autocomplete_fields = ["session"]

    def changelist_view(self, request: HttpRequest, extra_context=None) -> HttpResponse:
        # Affichage des inscriptions de la semaine courante par défaut
        if not request.GET:
            params = {
                "session__year": GlobalState.get_year(),
                "session__week": GlobalState.get_week(),
            }
            return redirect(f"{request.path}?{urlencode(params)}")
        return super().changelist_view(request, extra_context)

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet):
        """
        Permet d'appliquer la logique de suppression de SessionRegistration.delete()
        """
        for obj in queryset:
            self.delete_model(request, obj)


admin.site.register(GlobalState)
