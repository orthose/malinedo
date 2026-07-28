from django.db import models

from accounts.models import User
from booking.models import GlobalState, SessionRegistration, WeeklySession


WeekSchedule = list[WeeklySession]


class WeekScheduleQuery:
    """
    Objet de requête de planning des séances et inscriptions pour une semaine et un utilisateur donnés.

    Pour la semaine courante et les semaines passées, on requête simplement les séances de la semaine.
    Pour une semaine future, on fusionne la semaine courante avec la semaine future.

    Attention: On se contente de requêter tel quel les modèles en ne faisant que le strict
    nécessaire de modification des instances de modèle en mémoire. Le reste de la logique doit être
    implémenté dans WeeklySession.clean() et SessionRegistration.clean() au moment de la création
    ou de la modification d'une séance ou d'une inscription.
    """

    def __init__(self, year: int, week: int, user: User, **session_filters):
        """
        :param year: Année de consultation
        :param week: Semaine de consultation
        :param user: Utilisateur pour lequel construire le planning
        :param session_filters:
            Filtres supplémentaires à appliquer aux séances.
            Ils ne doivent pas inclure year et week.
        """
        self.year = year
        self.week = week
        self.user = user
        self.session_filters = session_filters
        self.is_future_week = GlobalState.is_future_week(year, week)

    def __get_queryset_schedule(
        self, year: int, week: int
    ) -> models.QuerySet[WeeklySession]:
        """
        Construit le QuerySet de WeeklySessionPrefetchedRegistrations pour une semaine donnée.
        """
        # Une semaine classique est une semaine qui ne nécessite pas de filtres particuliers et de corrections en mémoire
        # C'est le cas si on requête le planning de la semaine courante ou d'une semaine passée
        # ou le planning d'une semaine future et qu'on filtre sur les séances futures
        # Si is_classic_week==False on requête le planning d'une semaine future et on filtre sur les séances de la semaine courante
        # Dans ce cas on reporte dans le futur les séances et inscriptions de la semaine courante
        is_classic_week = not self.is_future_week or (
            self.year == year and self.week == week
        )

        user_registration_filters = (
            # Pour les semaines classiques pas de filtre
            {}
            if is_classic_week
            # Seules les inscriptions régulières de l'utilisateur sont reportées dans le futur
            else {"is_regular": True}
        )

        swimmers_registration_filters = (
            # Pour les semaines classiques on ne garde pas les inscriptions annulées
            {"is_cancelled": False}
            if is_classic_week
            # Seules les inscriptions régulières des nageurs sont reportées dans le futur
            else {"is_regular": True}
        )

        return (
            WeeklySession.objects.filter(year=year, week=week, **self.session_filters)
            .distinct()  # TODO: A quoi ça sert ? Normalement à rien car group est devenu singulier
            .select_related("group")
            .order_by("weekday", "start_hour")
            # Prefetch se charge de joindre par clé étrangère session
            # donc pas besoin de préciser les filtres year et week
            .prefetch_related(
                # Crée le champ swimmer_registration
                # Si le nageur n'est pas inscrit à la session la liste est vide
                # Sinon la liste contient un seul enregistrement (contrainte unicité)
                models.Prefetch(
                    "sessionregistration_set",
                    queryset=SessionRegistration.objects.filter(
                        swimmer=self.user, **user_registration_filters
                    ).only("is_regular", "is_cancelled", "swimmer_is_coach"),
                    to_attr="user_registration",
                )
            )
            .prefetch_related(
                # Liste des entraîneurs triés par création
                models.Prefetch(
                    "sessionregistration_set",
                    queryset=SessionRegistration.objects.filter(
                        swimmer_is_coach=True,
                        **swimmers_registration_filters,
                    )
                    .select_related("swimmer")
                    .order_by("pk"),
                    to_attr="coach_registrations",
                )
            )
            .prefetch_related(
                # Liste des nageurs triés par création
                models.Prefetch(
                    "sessionregistration_set",
                    queryset=SessionRegistration.objects.filter(
                        swimmer_is_coach=False,
                        **swimmers_registration_filters,
                    )
                    .select_related("swimmer")
                    .order_by("pk"),
                    to_attr="swimmer_registrations",
                )
            )
            # TODO: Ajouter plus tard swimmers_cancelled_registration
        )

    def get_schedule(self) -> WeekSchedule:
        """
        Renvoie le planning pour une semaine donnée.
        """
        schedule_requested_week = list(
            self.__get_queryset_schedule(self.year, self.week)
        )

        if self.is_future_week:

            def session_key(session: WeeklySession) -> tuple:
                """
                Une séance de la semaine courante est considérée comme associée
                à une séance future lorsque leurs champs d'unicité sans la dimension temporelle
                (session.group, session.weekday, session.start_hour) correspondent.
                """
                return (session.group, session.weekday, session.start_hour)

            def reset_registrations(
                current_registrations: list[SessionRegistration],
            ) -> None:
                """
                Réinitialise les inscriptions de la séance de la semaine courante.
                """
                for registration in current_registrations:
                    # Dans le futur les inscriptions ne sont pas annulées
                    registration.is_cancelled = False

            def import_registrations(
                current_registrations: list[SessionRegistration],
                future_registrations: list[SessionRegistration],
            ) -> None:
                """
                Importe les inscriptions régulières de la séance
                de la semaine courante dans les inscriptions de la séance future
                """
                future_registered_swimmers = set(
                    registration.swimmer for registration in future_registrations
                )
                future_registrations.extend(
                    [
                        registration
                        for registration in current_registrations
                        if registration.swimmer not in future_registered_swimmers
                    ]
                )

            current_year = GlobalState.get_year()
            current_week = GlobalState.get_week()
            schedule_current_week = list(
                self.__get_queryset_schedule(
                    current_year,
                    current_week,
                )
            )

            future_sessions = {
                session_key(session): session for session in schedule_requested_week
            }

            schedule_future_week = list()

            for session in schedule_current_week:
                future_session = future_sessions.get(session_key(session))
                # On corrige les séances et inscriptions de la semaine courante qui n'ont pas d'inscription future associée
                if future_session is None:
                    session.year = self.year
                    session.week = self.week
                    session.is_cancelled = False

                    reset_registrations(session.user_registration)
                    reset_registrations(session.coach_registrations)
                    reset_registrations(session.swimmer_registrations)

                    schedule_future_week.append(session)

                # Une séance future est associée à la séance de la semaine courante
                else:
                    # TODO: refactoriser ?
                    reset_registrations(session.user_registration)
                    reset_registrations(session.coach_registrations)
                    reset_registrations(session.swimmer_registrations)

                    import_registrations(
                        session.user_registration,
                        future_session.user_registration,
                    )
                    import_registrations(
                        session.coach_registrations,
                        future_session.coach_registrations,
                    )
                    import_registrations(
                        session.swimmer_registrations,
                        future_session.swimmer_registrations,
                    )

            # TODO: Il ne faut rajouter que les séances futures qui n'ont pas de séance courante associée
            # On ajoute toutes les séances futures qui écrasent les séances de la semaine courante
            # ou qui n'ont pas de séances de la semaine courante associée
            schedule_future_week.extend(schedule_requested_week)

            return schedule_future_week

        return schedule_requested_week
