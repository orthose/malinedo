from django.contrib import admin
from django.http import HttpRequest
from django.db.models.query import QuerySet

from .models import (
    WeeklySession,
    WeeklySessionHistory,
    SessionRegistration,
    SessionRegistrationHistory,
    GlobalSetting,
)


class WeeklySessionAdmin(admin.ModelAdmin):
    ordering = [
        "weekday",
        "start_hour",
        "group",
    ]
    list_filter = [
        "weekday",
        "group",
    ]
    actions = ["lock_sessions", "unlock_sessions"]

    @admin.action(description="Verrouiller les sessions hebdomadaires sélectionnées")
    def lock_sessions(self, request: HttpRequest, queryset: QuerySet[WeeklySession]):
        queryset.update(is_cancelled=True)

    @admin.action(description="Déverrouiller les sessions hebdomadaires sélectionnées")
    def unlock_sessions(self, request: HttpRequest, queryset: QuerySet[WeeklySession]):
        queryset.update(is_cancelled=False)


class WeeklySessionHistoryAdmin(admin.ModelAdmin):
    list_filter = [
        "year",
        "week",
        "weekday",
        "group",
    ]


class SessionRegistrationAdmin(admin.ModelAdmin):
    ordering = [
        "session__weekday",
        "session__start_hour",
        "session__group",
        "pk",
    ]
    search_fields = [
        "swimmer__first_name",
        "swimmer__last_name",
    ]
    list_filter = [
        "session__weekday",
        "session__group",
        "is_regular",
        "is_cancelled",
        "swimmer_is_coach",
    ]


class SessionRegistrationHistoryAdmin(admin.ModelAdmin):
    search_fields = [
        "swimmer__first_name",
        "swimmer__last_name",
        "session__year",
        "session__week",
    ]
    list_filter = [
        "session__year",
        "session__week",
        "session__group",
        "is_regular",
        "is_cancelled",
        "swimmer_is_coach",
    ]


admin.site.register(WeeklySession, WeeklySessionAdmin)
admin.site.register(WeeklySessionHistory, WeeklySessionHistoryAdmin)
admin.site.register(SessionRegistration, SessionRegistrationAdmin)
admin.site.register(SessionRegistrationHistory, SessionRegistrationHistoryAdmin)
admin.site.register(GlobalSetting)
