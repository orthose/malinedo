from django.db import models
from django.http import HttpRequest, HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import (
    AbstractWeeklySession,
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
def schedule(request: HttpRequest, show_history_filters: bool) -> HttpResponse:
    # Formulaire de filtrage
    schedule_form = (
        ScheduleForm(request.GET)
        if len(request.GET) > 0
        else ScheduleForm(
            {
                "mysessions": request.session.get("mysessions", default=False),
                "year": GlobalSetting.get_year(),
                "week": GlobalSetting.get_week(),
            }
        )
    )

    sessions = None
    is_current_week = True
    # Vérification du formulaire
    if schedule_form.is_valid():
        filters = {}
        weekly_session_model = WeeklySession
        session_registration_model = SessionRegistration

        # Enregistrement dans la session utilisateur du filtre des séances
        request.session["mysessions"] = schedule_form.cleaned_data["mysessions"]

        # Semaine courante
        if (
            schedule_form.cleaned_data["year"] == GlobalSetting.get_year()
            and schedule_form.cleaned_data["week"] == GlobalSetting.get_week()
        ):
            weekly_session_model = WeeklySession
            session_registration_model = SessionRegistration
        # Historique
        else:
            is_current_week = False
            weekly_session_model = WeeklySessionHistory
            session_registration_model = SessionRegistrationHistory
            filters["year"] = schedule_form.cleaned_data["year"]
            filters["week"] = schedule_form.cleaned_data["week"]

        # Filtre des séances du nageur
        if schedule_form.cleaned_data["mysessions"]:
            filters[f"{session_registration_model.__name__.lower()}__swimmer"] = (
                request.user
            )

        # Filtre des groupes du nageur
        filters["group__in"] = [
            group
            for group in AbstractWeeklySession.GROUP.keys()
            if request.user.has_perm(RegisterPermission.get_perm(group))
        ]

        # Requête à la base de données des séances
        sessions = (
            weekly_session_model.objects.filter(**filters)
            .order_by("weekday", "start_hour", "group")
            # Prefetch se charge de joindre par clé étrangère session
            # donc pas besoin de préciser les filtres year et week
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
            .prefetch_related(
                # Liste des entraîneurs triés par création
                models.Prefetch(
                    f"{session_registration_model.__name__.lower()}_set",
                    queryset=session_registration_model.objects.filter(
                        is_cancelled=False,
                        swimmer_is_coach=True,
                    )
                    .only("swimmer", "is_regular")
                    .order_by("pk"),
                    to_attr="coaches_registration",
                )
            )
            .prefetch_related(
                # Liste des nageurs triés par création
                models.Prefetch(
                    f"{session_registration_model.__name__.lower()}_set",
                    queryset=session_registration_model.objects.filter(
                        is_cancelled=False,
                        swimmer_is_coach=False,
                    )
                    .only("swimmer", "is_regular")
                    .order_by("pk"),
                    to_attr="swimmers_registration",
                )
            )
        )

    # Formulaire invalide
    else:
        sessions = WeeklySession.objects.none()

    # Séances par jour de la semaine
    weekday_sessions = {weekday: [] for weekday in WeeklySession.WEEKDAY.values()}

    for session in sessions:
        session.group = WeeklySession.GROUP[session.group]
        # Attributs dynamiques de session pour le template
        setattr(
            session,
            "background_is_colored",
            session.is_cancelled or session.swimmer_registration,
        )

        weekday_sessions[WeeklySession.WEEKDAY[session.weekday]].append(session)

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
        "show_history_filters": show_history_filters,
        "weekday_sessions": weekday_sessions,
        "is_current_week": is_current_week,
        "has_perm_coach": request.user.has_perm("booking." + RegisterPermission.COACH),
        "groups": request.user.groups.order_by("pk").all(),
    }

    return render(request, "booking/schedule.html", context)


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
                registration = SessionRegistration.objects.filter(
                    swimmer=request.user, session=session
                )
                # On ne peut supprimer une inscription que si on l'a annulée
                if registration.exists() and registration[0].is_cancelled:
                    registration[0].delete()

            return redirect(request.GET["next"])

    raise Http404


@login_required
def notice(request: HttpRequest) -> HttpRequest:
    return render(request, "booking/notice.html")
