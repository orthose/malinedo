from django.db import models
from django.http import HttpRequest, HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import (
    ClubGroup,
    RegisterPermission,
    WeeklySession,
    SessionRegistration,
    WeeklySessionHistory,
    SessionRegistrationHistory,
    GlobalSetting,
)
from .forms import (
    ScheduleForm,
    EditSessionRegistrationForm,
)


@login_required
def home(request: HttpRequest) -> HttpResponse:
    weekday_sessions = {weekday: [] for weekday in WeeklySession.WEEKDAY.values()}

    schedule_form = (
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

    schedule_form.filter_group_choices(request.user)

    sessions = None
    is_current_week = True
    if schedule_form.is_valid():
        filters = {}
        weekly_session_model = WeeklySession
        session_registration_model = SessionRegistration

        if (
            schedule_form.cleaned_data["year"] == GlobalSetting.get_year()
            and schedule_form.cleaned_data["week"] == GlobalSetting.get_week()
        ):
            weekly_session_model = WeeklySession
            session_registration_model = SessionRegistration
        else:
            is_current_week = False
            weekly_session_model = WeeklySessionHistory
            session_registration_model = SessionRegistrationHistory
            filters["year"] = schedule_form.cleaned_data["year"]
            filters["week"] = schedule_form.cleaned_data["week"]

        match schedule_form.cleaned_data["sessions"]:
            case ScheduleForm.SessionFilter.MY:
                filters[f"{session_registration_model.__name__.lower()}__swimmer"] = (
                    request.user
                )

        if schedule_form.cleaned_data["group"] != ScheduleForm.GroupFilter.ALL:
            filters["group"] = schedule_form.cleaned_data["group"]
        else:
            groups = [group for group, _ in schedule_form.fields["group"].choices]
            groups.remove("A")
            filters["group__in"] = groups

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
        "schedule_form": schedule_form,
        "weekday_sessions": weekday_sessions,
        "is_current_week": is_current_week,
        "has_perm_coach": request.user.has_perm("booking." + RegisterPermission.COACH),
        "is_board_member": request.user.groups.filter(name=ClubGroup.BOARD),
    }

    return render(request, "booking/home.html", context)


@login_required
def edit(request: HttpRequest) -> HttpResponse:
    if request.method == "POST" and "next" in request.GET:
        form = EditSessionRegistrationForm(request.POST)

        if form.is_valid():
            session = get_object_or_404(
                WeeklySession, pk=form.cleaned_data["session_id"]
            )

            fields = {}
            for field in ["is_regular", "is_cancelled", "swimmer_is_coach"]:
                if field in request.POST:
                    fields[field] = form.cleaned_data[field]

            if (
                # Si le nageur veut s'inscire en tant qu'entraîneur en a-t-il la permission ?
                (
                    not form.cleaned_data["swimmer_is_coach"]
                    or request.user.has_perm("booking." + RegisterPermission.COACH)
                )
                # Est-ce que la nageur a la permission de s'inscrire en fonction de ses groupes ?
                and request.user.has_perm(RegisterPermission.get_perm(session.group))
                # S'il s'agit d'une inscription est-ce que le nageur a déjà un entraînement prévu à la même heure le même jour ?
                and (
                    "is_regular" not in fields
                    or not SessionRegistration.objects.filter(
                        swimmer=request.user,
                        session__weekday=session.weekday,
                        session__start_hour=session.start_hour,
                    ).exists()
                )
            ):
                SessionRegistration.objects.update_or_create(
                    swimmer=request.user,
                    session=session,
                    defaults=fields,
                )

            if form.cleaned_data["remove"]:
                SessionRegistration.objects.filter(
                    swimmer=request.user, session=session
                ).delete()

            return redirect(request.GET["next"])

    raise Http404


@login_required
def notice(request: HttpRequest) -> HttpRequest:
    return render(request, "booking/notice.html")
