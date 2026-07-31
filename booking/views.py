from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
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
        "is_future_week": GlobalState.is_future_week(year, week),
        "is_coach": request.user.is_coach,
    }

    return render(request, "booking/schedule.html", context)


@login_required
@transaction.atomic
def edit(request: HttpRequest) -> HttpResponse:
    request.user = cast(User, request.user)

    if request.method == "POST" and "next" in request.GET:
        form = EditSessionRegistrationForm(request.POST)

        if form.is_valid():
            session = WeeklySession.objects.get(pk=form.cleaned_data["session_id"])

            # Suppression de l'inscription
            if form.cleaned_data["remove"]:
                registration = SessionRegistration.objects.get(
                    swimmer=request.user, session=session
                )
                # On ne peut supprimer une inscription que si on l'a annulée
                if registration.is_cancelled:
                    registration.delete()

            # Création ou modification de l'inscription
            else:
                registration_fields = {}

                if GlobalState.is_future_week(
                    form.cleaned_data["year"], form.cleaned_data["week"]
                ):
                    # L'inscription future n'existe pas encore et on l'annule
                    # Comme c'est une inscription importée de la semaine courante
                    # on importe les champs de cette inscription
                    try:
                        registration = SessionRegistration.objects.get(
                            swimmer=request.user,
                            # On ne peut pas filtrer simplement par session
                            # car cela peut être une session courant ou future
                            # Or on veut récupérer l'inscription de la séance courante
                            session__year=GlobalState.get_year(),
                            session__week=GlobalState.get_week(),
                            session__group=session.group,
                            session__weekday=session.weekday,
                            session__start_hour=session.start_hour,
                        )
                        for field in ["is_regular", "is_cancelled", "swimmer_is_coach"]:
                            registration_fields[field] = getattr(registration, field)

                    # Si l'inscription courante n'existe pas on ne fait rien
                    # Les champs seront complétés par le formulaire
                    except SessionRegistration.DoesNotExist:
                        pass

                    # L'inscription concerne une séance de la semaine courante pour une semaine future
                    if GlobalState.is_current_week(session.year, session.week):
                        # Il faut créer la séance future associée
                        session = WeeklySession.objects.create(
                            year=form.cleaned_data["year"],
                            week=form.cleaned_data["week"],
                            group=session.group,
                            weekday=session.weekday,
                            start_hour=session.start_hour,
                            stop_hour=session.stop_hour,
                            capacity=session.capacity,
                            is_cancelled=False,
                        )
                        # Des vérifications sont faites dans WeeklySession.clean()
                        session.full_clean()

                for field in ["is_regular", "is_cancelled", "swimmer_is_coach"]:
                    if field in request.POST:
                        registration_fields[field] = form.cleaned_data[field]

                if registration_fields:
                    registration, _ = SessionRegistration.objects.update_or_create(
                        swimmer=request.user,
                        session=session,
                        defaults=registration_fields,
                    )
                    # Des vérifications sont faites dans SessionRegistration.clean()
                    registration.full_clean()

            # Permet de garder les arguments year et week
            return redirect(request.GET["next"])

    return HttpResponseBadRequest("Formulaire d'édition d'inscription invalide")


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
