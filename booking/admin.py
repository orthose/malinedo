from django.contrib import admin
from django.http import HttpRequest
from django.db.models.query import QuerySet

from .models import (
    SessionGroup,
    WeeklySession,
    SessionRegistration,
    GlobalState,
)


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
    actions = ["lock_sessions", "unlock_sessions"]

    # TODO: Renommer en Annuler
    @admin.action(description="Verrouiller les sessions hebdomadaires sélectionnées")
    def lock_sessions(self, request: HttpRequest, queryset: QuerySet[WeeklySession]):
        queryset.update(is_cancelled=True)

    # TODO: Restaurer ? C'est quoi le contraire d'Annuler ?
    @admin.action(description="Déverrouiller les sessions hebdomadaires sélectionnées")
    def unlock_sessions(self, request: HttpRequest, queryset: QuerySet[WeeklySession]):
        queryset.update(is_cancelled=False)


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


admin.site.register(GlobalState)
