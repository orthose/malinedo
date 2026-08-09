from collections.abc import Iterator

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

    def __init__(self, year: int, week: int, user: User, only_user_sessions: bool):
        """
        :param year: Année de consultation
        :param week: Semaine de consultation
        :param user: Utilisateur pour lequel construire le planning
        :param only_user_sessions:
            Filtre pour ne garder que les séances auxquelles est inscrit l'utilisateur
        """
        self.year = year
        self.week = week
        self.user = user
        self.only_user_sessions = only_user_sessions
        self.is_future_week = GlobalState.is_future_week(year, week)
        self.schedule: WeekSchedule = None

    def __iter__(self) -> Iterator[WeeklySession]:
        return iter(self.schedule)

    def __get_queryset_schedule(
        self, year: int, week: int
    ) -> models.QuerySet[WeeklySession]:
        """
        Construit le QuerySet de WeeklySession enrichi pour une semaine donnée.
        """
        session_filters = (
            {"sessionregistration__swimmer": self.user}
            if self.only_user_sessions and not GlobalState.is_future_week(year, week)
            else {}
        )

        user_registration_filters = (
            # Seules les inscriptions régulières de l'utilisateur de la semaine courante sont reportées dans le futur
            {"is_regular": True}
            if self.is_future_week and GlobalState.is_current_week(year, week)
            # Pas de filtre dans tous les autres cas
            else {}
        )

        swimmers_registration_filters = (
            # Seules les inscriptions régulières des nageurs de la semaine courante sont reportées dans le futur
            {"is_regular": True}
            if self.is_future_week and GlobalState.is_current_week(year, week)
            # Si on requête les séances futures alors on filtrera dans get_schedule
            # après l'import des inscriptions de la semaine courante dans la semaine future
            else {}
            if self.is_future_week and GlobalState.is_future_week(year, week)
            # Pour les semaines classiques on ne garde pas les inscriptions annulées
            else {"is_cancelled": False}
        )

        return (
            WeeklySession.objects.filter(
                models.Q(group__groups__in=self.user.groups.all())
                | models.Q(group__isnull=True),
                year=year,
                week=week,
                **session_filters,
            )
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
            # TODO: Ajouter plus tard swimmer_cancelled_registrations
        )

    def __session_key(self, session: WeeklySession) -> tuple:
        """
        Une séance de la semaine courante est considérée comme associée
        à une séance future lorsque leurs champs d'unicité sans la dimension temporelle
        (session.group, session.weekday, session.start_hour) correspondent.
        """
        return (session.group, session.weekday, session.start_hour)

    def __reset_registrations(
        self,
        registrations: list[SessionRegistration],
    ) -> None:
        """
        Réinitialise les inscriptions de la séance de la semaine courante.
        """
        for reg in registrations:
            # Dans le futur les inscriptions ne sont pas annulées
            reg.is_cancelled = False

    def __import_registrations(
        self,
        current_registrations: list[SessionRegistration],
        future_registrations: list[SessionRegistration],
    ) -> None:
        """
        Importe les inscriptions régulières de la séance de la semaine courante
        dans les inscriptions de la séance future.
        """
        future_registered_swimmers = set(reg.swimmer for reg in future_registrations)
        future_registrations.extend(
            [
                reg
                for reg in current_registrations
                if reg.swimmer not in future_registered_swimmers
            ]
        )

    def __delete_cancelled_registrations(
        self,
        registrations: list[SessionRegistration],
    ) -> None:
        """
        Supprime toutes les inscriptions annulées.
        """
        registrations[:] = [reg for reg in registrations if not reg.is_cancelled]

    def load_schedule(self) -> None:
        """
        Charge le planning pour une semaine donnée.
        """
        schedule_requested_week = list(
            self.__get_queryset_schedule(self.year, self.week)
        )
        self.schedule = schedule_requested_week

        if self.is_future_week:
            current_year = GlobalState.get_year()
            current_week = GlobalState.get_week()
            schedule_current_week = list(
                self.__get_queryset_schedule(
                    current_year,
                    current_week,
                )
            )

            future_sessions = {
                self.__session_key(session): session
                for session in schedule_requested_week
            }

            schedule_future_week: WeekSchedule = list()

            for session in schedule_current_week:
                future_session = future_sessions.get(self.__session_key(session))

                # On corrige les séances et inscriptions de la semaine courante qui n'ont pas d'inscription future associée
                if future_session is None:
                    session.year = self.year
                    session.week = self.week
                    session.is_cancelled = False

                    self.__reset_registrations(session.user_registration)
                    self.__reset_registrations(session.coach_registrations)
                    self.__reset_registrations(session.swimmer_registrations)

                    # On ajoute la séance au planning
                    schedule_future_week.append(session)

                # Une séance future est associée à la séance de la semaine courante
                # On modifie en place la séance future et ses inscriptions
                else:
                    self.__reset_registrations(session.user_registration)
                    self.__reset_registrations(session.coach_registrations)
                    self.__reset_registrations(session.swimmer_registrations)

                    self.__import_registrations(
                        session.user_registration,
                        future_session.user_registration,
                    )
                    self.__import_registrations(
                        session.coach_registrations,
                        future_session.coach_registrations,
                    )
                    self.__import_registrations(
                        session.swimmer_registrations,
                        future_session.swimmer_registrations,
                    )

                    self.__delete_cancelled_registrations(
                        future_session.coach_registrations
                    )
                    self.__delete_cancelled_registrations(
                        future_session.swimmer_registrations
                    )

            # On ajoute au planning toutes les séances futures
            schedule_future_week.extend(schedule_requested_week)

            if self.only_user_sessions:
                # On supprime les séances futures auquel le nageur n'est pas inscrit
                schedule_future_week[:] = [
                    session
                    for session in schedule_future_week
                    if len(session.user_registration) > 0
                ]

            self.schedule = schedule_future_week

    @property
    def user_registration_count(self) -> int:
        res = 0

        for session in self.schedule:
            if not session.is_cancelled and session.user_registration:
                reg = session.user_registration[0]
                if not reg.is_cancelled and not reg.swimmer_is_coach:
                    res += 1

        return res
