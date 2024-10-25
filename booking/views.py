import datetime
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import (
    WeeklySession,
    SessionRegistration,
    WeeklySessionHistory,
    SessionRegistrationHistory,
    GlobalSetting,
)
from .forms import ScheduleForm


@login_required
def home(request: HttpRequest) -> HttpResponse:
    weekday_sessions = {weekday: [] for weekday in WeeklySession.WEEKDAY.values()}

    form = (
        ScheduleForm(request.GET)
        if len(request.GET) > 0
        else ScheduleForm(
            {
                "sessions": "my",
                "group": "A",
                "year": GlobalSetting.get_year(),
                "week": GlobalSetting.get_week(),
            }
        )
    )

    # TODO: Ne pas proposer les groupes auxquels n'appartient pas le nageur
    # Retirer Tous si le nageur n'appartient qu'à un groupe
    # print(context["form"].fields["group"].choices)

    sessions = None
    if form.is_valid():
        filters = {}
        weekly_session_model = WeeklySession
        session_registration_model = SessionRegistration

        if (
            form.cleaned_data["year"] == GlobalSetting.get_year()
            and form.cleaned_data["week"] == GlobalSetting.get_week()
        ):
            weekly_session_model = WeeklySession
            session_registration_model = SessionRegistration
        else:
            weekly_session_model = WeeklySessionHistory
            session_registration_model = SessionRegistrationHistory
            filters["year"] = form.cleaned_data["year"]
            filters["week"] = form.cleaned_data["week"]

        match form.cleaned_data["sessions"]:
            case ScheduleForm.SessionFilter.MY:
                filters[f"{session_registration_model.__name__.lower()}__swimmer"] = (
                    request.user
                )

        if form.cleaned_data["group"] != ScheduleForm.GroupFilter.ALL:
            filters["group"] = form.cleaned_data["group"]

        sessions = (
            weekly_session_model.objects.filter(**filters)
            .order_by("weekday", "start_hour", "group")
            .prefetch_related(
                # Crée le champ swimmer_registration
                # Si le nageur n'est pas inscrit à la session la liste est vide
                # Sinon la liste contient un seul enregistrement (contrainte unicité)
                models.Prefetch(
                    f"{session_registration_model.__name__.lower()}_set",
                    queryset=session_registration_model.objects.filter(
                        swimmer=request.user
                    ).only("is_regular", "is_cancelled", "swimmer_is_coach"),
                    to_attr="swimmer_registration",
                )
            )
        )

    else:
        sessions = WeeklySession.objects.none()

    for session in sessions:
        session.group = WeeklySession.GROUP[session.group]
        weekday_sessions[WeeklySession.WEEKDAY[session.weekday]].append(session)

    context = {
        "form": form,
        "weekday_sessions": weekday_sessions,
    }

    return render(request, "booking/home.html", context)
