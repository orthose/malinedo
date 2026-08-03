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

    week_schedule_query = None

    # Vérification du formulaire
    if schedule_form.is_valid():
        # Enregistrement dans la session utilisateur du filtre des séances
        request.session["mysessions"] = schedule_form.cleaned_data["mysessions"]

        year = schedule_form.cleaned_data["year"]
        week = schedule_form.cleaned_data["week"]

        # Requête du planning des séances et inscriptions pour la semaine
        week_schedule_query = WeekScheduleQuery(
            year,
            week,
            request.user,
            only_user_sessions=schedule_form.cleaned_data["mysessions"],
        )
        week_schedule_query.load_schedule()

    # Formulaire invalide
    else:
        return HttpResponseBadRequest("Formulaire de planning invalide")

    # Séances par jour de la semaine
    weekday_sessions = {weekday: [] for weekday in WeeklySession.WEEKDAY.values()}

    for session in week_schedule_query:
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
        "user_registration_count": week_schedule_query.user_registration_count,
    }

    return render(request, "booking/schedule.html", context)


@login_required
@transaction.atomic
def edit(request: HttpRequest) -> HttpResponse:
    """
    TODO: Mettre une limite de date d'annulation dans le futur
    qui s'arrête à la fin de la saison
    """
    request.user = cast(User, request.user)

    if request.method == "POST" and "next" in request.GET:
        form = EditSessionRegistrationForm(request.POST)

        if (
            form.is_valid()
            # On ne peut pas modifier une semaine passée
            and not GlobalState.is_past_week(
                form.cleaned_data["year"], form.cleaned_data["week"]
            )
        ):
            session = WeeklySession.objects.get(pk=form.cleaned_data["session_id"])

            # Suppression de l'inscription
            if form.cleaned_data["remove"]:
                reg = SessionRegistration.objects.get(
                    swimmer=request.user, session=session
                )

                if not reg.is_cancelled:
                    return HttpResponseBadRequest(
                        "Une inscription ne peut être supprimée que si elle est annulée"
                    )

                reg.delete()

            # Création ou modification de l'inscription
            else:
                registration_fields = {}

                if GlobalState.is_future_week(
                    form.cleaned_data["year"], form.cleaned_data["week"]
                ):
                    # L'inscription future n'existe pas encore et on l'annule
                    # Comme c'est une inscription importée de la semaine courante
                    # on importe les champs de cette inscription
                    reg = SessionRegistration.objects.filter(
                        swimmer=request.user,
                        # On ne peut pas filtrer simplement par session
                        # car cela peut être une session courant ou future
                        # Or on veut récupérer l'inscription de la séance courante
                        session__year=GlobalState.get_year(),
                        session__week=GlobalState.get_week(),
                        session__group=session.group,
                        session__weekday=session.weekday,
                        session__start_hour=session.start_hour,
                    ).first()

                    # Si l'inscription courante n'existe pas on ne fait rien
                    # Les champs seront complétés par le formulaire
                    if reg:
                        for field in ["is_regular", "is_cancelled", "swimmer_is_coach"]:
                            registration_fields[field] = getattr(reg, field)

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
                    reg = SessionRegistration.objects.filter(
                        swimmer=request.user,
                        session=session,
                    ).first()

                    if (
                        reg
                        and reg.is_cancelled
                        and "is_cancelled" in registration_fields
                        and not registration_fields["is_cancelled"]
                    ):
                        return HttpResponseBadRequest(
                            "Une inscription annulée doit être supprimée avant d'être renouvelée"
                        )

                    reg, _ = SessionRegistration.objects.update_or_create(
                        swimmer=request.user,
                        session=session,
                        defaults=registration_fields,
                    )
                    # Des vérifications sont faites dans SessionRegistration.clean()
                    reg.full_clean()

            # Permet de garder les arguments year et week lors de la redirection
            return redirect(request.GET["next"])

    return HttpResponseBadRequest("Formulaire d'édition d'inscription invalide")


@login_required
def groups(request: HttpRequest) -> HttpRequest:
    context = {
        "session_groups": SessionGroup.objects.filter(
            groups__in=request.user.groups.all()
        ),
        "admins": User.objects.filter(is_staff=True, is_superuser=False),
    }

    return render(request, "booking/groups.html", context)


@login_required
def help(request: HttpRequest) -> HttpRequest:
    return render(request, "booking/help.html")
