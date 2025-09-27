from django.contrib import admin
from django.forms import ModelForm, ValidationError
from django.http import HttpRequest
from django.db.models.query import QuerySet

from .models import (
    SessionGroup,
    WeeklySession,
    WeeklySessionHistory,
    SessionRegistration,
    SessionRegistrationHistory,
    GlobalSetting,
)


@admin.register(SessionGroup)
class SessionGroupAdmin(admin.ModelAdmin):
    list_filter = ["group"]


class WeeklySessionAdminForm(ModelForm):
    UNIQUE_FIELDS = ["weekday", "start_hour"]

    def clean(self):
        """
        Vérifie la contrainte d'unicité des séances.

        On ne peut pas effectuer cette vérification en base
        à cause de la relation m2m de WeeklySession.groups.
        """
        concurrent_sessions = WeeklySession.objects.filter(
            **{field: self.cleaned_data[field] for field in self.UNIQUE_FIELDS}
        )

        groups_set = set(self.cleaned_data["groups"])

        for session in concurrent_sessions:
            if groups_set == set(session.groups.all()):
                raise ValidationError("Une séance similaire existe déjà")


class WeeklySessionHistoryAdminForm(WeeklySessionAdminForm):
    UNIQUE_FIELDS = ["weekday", "start_hour", "year", "week"]


@admin.register(WeeklySession)
class WeeklySessionAdmin(admin.ModelAdmin):
    form = WeeklySessionAdminForm
    ordering = [
        "weekday",
        "start_hour",
    ]
    list_filter = [
        "weekday",
        "groups",
    ]
    actions = ["lock_sessions", "unlock_sessions"]

    @admin.action(description="Verrouiller les sessions hebdomadaires sélectionnées")
    def lock_sessions(self, request: HttpRequest, queryset: QuerySet[WeeklySession]):
        queryset.update(is_cancelled=True)

    @admin.action(description="Déverrouiller les sessions hebdomadaires sélectionnées")
    def unlock_sessions(self, request: HttpRequest, queryset: QuerySet[WeeklySession]):
        queryset.update(is_cancelled=False)


@admin.register(WeeklySessionHistory)
class WeeklySessionHistoryAdmin(admin.ModelAdmin):
    form = WeeklySessionHistoryAdminForm
    list_filter = [
        "year",
        "week",
        "weekday",
        "groups",
    ]


@admin.register(SessionRegistration)
class SessionRegistrationAdmin(admin.ModelAdmin):
    ordering = [
        "session__weekday",
        "session__start_hour",
        "pk",
    ]
    search_fields = [
        "swimmer__first_name",
        "swimmer__last_name",
    ]
    list_filter = [
        "session__weekday",
        "session__groups",
        "is_regular",
        "is_cancelled",
        "swimmer_is_coach",
    ]


@admin.register(SessionRegistrationHistory)
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
        "session__groups",
        "is_regular",
        "is_cancelled",
        "swimmer_is_coach",
    ]


admin.site.register(GlobalSetting)
