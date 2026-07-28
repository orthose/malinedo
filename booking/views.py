from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from typing import cast

from accounts.models import User
from .models import (
    SessionGroup,
    WeeklySession,
    SessionRegistration,
    GlobalState,
)
from .forms import (
    ScheduleForm,
    EditSessionRegistrationForm,
)
from .query import WeekScheduleQuery


@login_required
def schedule(request: HttpRequest) -> HttpResponse:
    request.user = cast(User, request.user)

    # Quelle est la semaine courante ?
    year = GlobalState.get_year()
    week = GlobalState.get_week()

    # Formulaire de filtrage
    schedule_form = (
        ScheduleForm(request.GET)
        if len(request.GET) > 0
        else ScheduleForm(
            {
                "mysessions": request.session.get("mysessions", default=False),
                "year": year,
                "week": week,
            }
        )
    )

    week_schedule = None

    # Vérification du formulaire
    if schedule_form.is_valid():
        session_filters = {}

        # Enregistrement dans la session utilisateur du filtre des séances
        request.session["mysessions"] = schedule_form.cleaned_data["mysessions"]

        year = schedule_form.cleaned_data["year"]
        week = schedule_form.cleaned_data["week"]

        # Filtre des séances du nageur
        if schedule_form.cleaned_data["mysessions"]:
            session_filters["sessionregistration__swimmer"] = request.user

        # Filtre des groupes du nageur
        # TODO: Gérer group = NULL
        session_filters["group__groups__in"] = request.user.groups.all()

        # Requête du planning des séances et inscriptions pour la semaine
        week_schedule = WeekScheduleQuery(
            year, week, request.user, **session_filters
        ).get_schedule()

    # Formulaire invalide
    else:
        return HttpResponseBadRequest("Formulaire de planning invalide")

    # Séances par jour de la semaine
    weekday_sessions = {weekday: [] for weekday in WeeklySession.WEEKDAY.values()}

    for session in week_schedule:
        session.background_is_colored = (
            session.is_cancelled or session.user_registration
        )
        weekday_sessions[session.french_weekday].append(session)

    # Attributs HTML pour les champs de formulaire du template
    schedule_form.fields["mysessions"].widget.attrs.update(
        {
            "class": "btn-check",
            "autocomplete": "off",
            # Soumission automatique du formulaire
            "onclick": "this.form.submit()",
        }
    )
    schedule_form.fields["year"].widget.attrs["class"] = "numberinput form-control"
    schedule_form.fields["week"].widget.attrs["class"] = "numberinput form-control"

    # Variables injectées dans le template
    context = {
        "schedule_form": schedule_form,
        "weekday_sessions": weekday_sessions,
        "is_current_week": GlobalState.is_current_week(year, week),
        "is_coach": request.user.is_coach,
    }

    return render(request, "booking/schedule.html", context)


@login_required
def edit(request: HttpRequest) -> HttpResponse:
    request.user = cast(User, request.user)

    if request.method == "POST" and "next" in request.GET:
        form = EditSessionRegistrationForm(request.POST)

        if form.is_valid():
            session = get_object_or_404(  # TODO: 404 est le bon code ?
                WeeklySession, pk=form.cleaned_data["session_id"]
            )

            fields = {}
            for field in ["is_regular", "is_cancelled", "swimmer_is_coach"]:
                if field in request.POST:
                    fields[field] = form.cleaned_data[field]

            # TODO: Ces vérifications sont faites dans SessionRegistration.clean
            if (
                # Si le nageur veut s'inscrire en tant qu'entraîneur en a-t-il la permission ?
                (not form.cleaned_data["swimmer_is_coach"] or request.user.is_coach)
                # Est-ce que le nageur a la permission de s'inscrire en fonction de ses groupes ?
                and set(
                    session_group.group for session_group in session.groups.all()
                ).intersection(set(request.user.groups.all()))
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
                registration = SessionRegistration.objects.filter(
                    swimmer=request.user, session=session
                )
                # On ne peut supprimer une inscription que si on l'a annulée
                if registration.exists() and registration[0].is_cancelled:
                    registration[0].delete()

            return redirect(request.GET["next"])

    raise Http404  # TODO: 404 est le bon code ?


@login_required
def groups(request: HttpRequest) -> HttpRequest:
    # TODO: La gestion des groupes a évolué
    context = {
        "session_groups": SessionGroup.objects.filter(
            group__in=request.user.groups.all()
        ),
        "admins": User.objects.filter(is_staff=True, is_superuser=False),
    }

    return render(request, "booking/groups.html", context)


@login_required
def help(request: HttpRequest) -> HttpRequest:
    return render(request, "booking/help.html")
