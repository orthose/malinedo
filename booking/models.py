import datetime
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


def get_year_field() -> models.Field:
    return models.IntegerField("année")


def get_week_field() -> models.Field:
    return models.PositiveSmallIntegerField(
        "semaine",
        validators=[
            MinValueValidator(1),
            MaxValueValidator(53),
        ],
    )


class SessionGroup(models.Model):
    """
    Groupe de niveau de nage

    En fonction du groupe auquel un nageur appartient,
    il ne peut pas s'inscrire à plus d'un certain
    nombre de séances par semaine
    """

    group = models.OneToOneField(Group, on_delete=models.CASCADE, verbose_name="Groupe")
    max_registrations_per_week = models.PositiveSmallIntegerField(
        verbose_name="Limite d'inscriptions hebdomadaires par nageur",
    )

    def __str__(self) -> str:
        return self.group.name

    @property
    def name(self) -> str:
        return self.group.name

    class Meta:
        verbose_name = "groupe de nage"
        verbose_name_plural = "groupes de nage"


class AbstractWeeklySession(models.Model):
    WEEKDAY = {
        1: "Lundi",
        2: "Mardi",
        3: "Mercredi",
        4: "Jeudi",
        5: "Vendredi",
        6: "Samedi",
        7: "Dimanche",
    }

    groups = models.ManyToManyField(SessionGroup, verbose_name="Groupes")
    weekday = models.PositiveSmallIntegerField("Jour", choices=WEEKDAY)
    start_hour = models.TimeField("Heure début")
    stop_hour = models.TimeField("Heure fin")
    capacity = models.PositiveSmallIntegerField("Capacité")
    is_cancelled = models.BooleanField("Est annulée ?", default=False)

    @property
    def group_names(self) -> list[str]:
        return [
            session_group.name for session_group in self.groups.order_by("pk").all()
        ]

    @property
    def duration(self) -> datetime.timedelta:
        dt_start_hour = datetime.datetime.combine(
            datetime.date(1, 1, 1), self.start_hour
        )
        dt_stop_hour = datetime.datetime.combine(datetime.date(1, 1, 1), self.stop_hour)
        return dt_stop_hour - dt_start_hour

    @property
    def total_swimmers(self) -> int:
        pass

    @property
    def registration_rate(self) -> int:
        return round(self.total_swimmers * 100 / self.capacity)

    @property
    def french_weekday(self) -> str:
        return self.WEEKDAY[self.weekday]

    @property
    def french_date(self) -> str:
        pass

    def __str__(self) -> str:
        groups_name = "|".join([group.name for group in self.groups.order_by("pk")])
        return f"[{groups_name}] {self.WEEKDAY[self.weekday]} {self.start_hour.strftime('%Hh%M')}-{self.stop_hour.strftime('%Hh%M')}"

    def clean(self):
        if self.start_hour >= self.stop_hour:
            raise ValidationError(
                "L'heure de début de séance doit être antérieure à l'heure de fin"
            )

    class Meta:
        abstract = True


class WeeklySession(AbstractWeeklySession):
    """
    Créneaux d'entraînement hebdomadaires définis en début d'année

    L'unicité de chaque créneau est défini par:
        + Groupes de niveau (ex: Loisir, Compétition)
        + Jour de la semaine
        + Heure de début

    La contrainte d'unicité est vérifiée côté formulaire admin.

    Les autres champs à compléter pour chaque créneau sont:
        + Heure de fin
        + Capacité (nombre de nageurs)

    Les autres champs diponibles pour chaque créneau sont:
        + Le créneau est-il annulé cette semaine ?
        + Durée de la séance
        + Nombre de nageurs inscrits
        + Taux d'inscriptions
        + Liste des nageurs inscrits
        + Liste des entraîneurs inscrits
    """

    @property
    def total_swimmers(self) -> int:
        return SessionRegistration.objects.filter(
            session=self, is_cancelled=False, swimmer_is_coach=False
        ).count()

    @property
    def french_date(self) -> str:
        return datetime.datetime.fromisocalendar(
            GlobalSetting.get_year(),
            GlobalSetting.get_week(),
            self.weekday,
        ).strftime("%d/%m/%Y")

    def save_to_history(self, year: int, week: int) -> "WeeklySessionHistory":
        session = self.__dict__.copy()
        session.pop("id")
        session.pop("_state")
        session["year"] = year
        session["week"] = week

        session_history = WeeklySessionHistory(**session)
        session_history.save()

        for session_group in self.groups.all():
            session_history.groups.add(session_group)

        return session_history

    class Meta:
        verbose_name = "session hebdomadaire"
        verbose_name_plural = "sessions hebdomadaires"
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_hour__lt=models.F("stop_hour")),
                name="check_weekly_session_start_hour_before_stop_hour",
            ),
        ]


class WeeklySessionHistory(AbstractWeeklySession):
    """
    Historique des sessions pour les statistiques
    """

    year = get_year_field()
    week = get_week_field()

    @property
    def total_swimmers(self) -> int:
        return SessionRegistrationHistory.objects.filter(
            session=self, is_cancelled=False, swimmer_is_coach=False
        ).count()

    @property
    def french_date(self) -> str:
        return datetime.datetime.fromisocalendar(
            self.year,
            self.week,
            self.weekday,
        ).strftime("%d/%m/%Y")

    def __str__(self) -> str:
        return f"{self.year}-{self.week} " + super().__str__()

    class Meta:
        verbose_name = "historique session hebdomadaire"
        verbose_name_plural = "historique sessions hebdomadaires"
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_hour__lt=models.F("stop_hour")),
                name="check_weekly_session_history_start_hour_before_stop_hour",
            ),
        ]


class AbstractSessionRegistration(models.Model):
    swimmer = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        verbose_name="Nageur",
    )
    session = models.ForeignKey(
        WeeklySession,
        on_delete=models.CASCADE,
        verbose_name="Session",
    )
    is_regular = models.BooleanField("Est régulière ?")
    is_cancelled = models.BooleanField("Est annulée ?", default=False)
    swimmer_is_coach = models.BooleanField("Est entraîneur ?", default=False)

    def __str__(self) -> str:
        if self.swimmer is None:
            return f"(Inconnu) {self.session}"
        return f"({self.swimmer.first_name} {self.swimmer.last_name.upper()}) {self.session}"

    class Meta:
        abstract = True

    @staticmethod
    def get_registration_model_for_week(
        year: int, week: int
    ) -> "AbstractSessionRegistration":
        """
        Récupère le modèle d'inscription pour une semaine donnée.

        :param year: Année de consultation
        :param week: Semaine de consultation
        :return: SessionRegistration ou SessionRegistrationHistory
        """
        current_year = GlobalSetting.get_year()
        current_week = GlobalSetting.get_week()
        if year < current_year or (year == current_year and week < current_week):
            return SessionRegistrationHistory
        return SessionRegistration

    @classmethod
    def get_registrations_for_week(cls, year: int, week: int) -> models.QuerySet:
        """
        Récupère les inscriptions pour une semaine donnée.
        Le modèle d'inscription est choisi en fonction de la semaine demandée.
        Dans le cas d'une semaine future, le champ is_cancelled
        est corrigé en fonction des annulations futures.

        :param year: Année de consultation
        :param week: Semaine de consultation
        :return: QuerySet d'inscriptions corrigé
        """
        registration_model = cls.get_registration_model_for_week(year, week)
        queryset = registration_model.objects.all()

        if registration_model == SessionRegistrationHistory:
            return queryset

        # TODO: Ne faire le traitement que si on consulte une semaine future
        future_cancelled_registration_ids = set(
            FutureCancelledRegularRegistration.objects.filter(
                registration__in=queryset,
                year=year,
                week=week,
            ).values_list("registration_id", flat=True)
        )

        for registration in queryset:
            registration.is_cancelled = (
                registration.pk in future_cancelled_registration_ids
            )

        return queryset


class SessionRegistration(AbstractSessionRegistration):
    """
    Inscription des nageurs aux entraînements de la semaine

    L'unicité de chaque inscription est définie par:
        + Nageur
        + Créneau

    Ainsi un nageur ne peut pas s'inscrire deux fois au même créneau

    Les autres champs à compléter pour chaque inscription sont:
        + Est-ce le créneau d'inscription habituel du nageur ?
        + Le nageur a-t-il annulé son inscription cette semaine ?
        + Le nageur est-il l'entraîneur de la séance ?
    """

    def to_history(self, session_history_pk: int) -> "SessionRegistrationHistory":
        registration = self.__dict__.copy()
        registration.pop("id")
        registration.pop("_state")
        registration["session_id"] = session_history_pk
        return SessionRegistrationHistory(**registration)

    class Meta:
        verbose_name = "inscription session"
        verbose_name_plural = "inscriptions sessions"
        constraints = [
            models.UniqueConstraint(
                "swimmer",
                "session",
                name="unique_swimmer_for_one_session",
            ),
        ]


class SessionRegistrationHistory(AbstractSessionRegistration):
    """
    Historique des inscriptions pour les statistiques
    """

    swimmer = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Nageur",
    )
    session = models.ForeignKey(
        WeeklySessionHistory,
        on_delete=models.CASCADE,
        verbose_name="Session historique",
    )

    class Meta:
        verbose_name = "historique inscription session"
        verbose_name_plural = "historique inscriptions sessions"
        constraints = [
            models.UniqueConstraint(
                "swimmer",
                "session",
                name="unique_swimmer_for_one_session_history",
            ),
        ]
        permissions = []


class FutureCancelledRegularRegistration(models.Model):
    """
    Annulation d'une inscription régulière dans les semaines à venir
    """

    registration = models.ForeignKey(
        SessionRegistration,
        # Si l'inscription est supprimée alors l'annulation future doit l'être également
        on_delete=models.CASCADE,
        verbose_name="Inscription régulière",
    )
    year = get_year_field()
    week = get_week_field()

    def clean(self):
        # Cette contrainte ne peut pas être vérifiée en base car elle nécessite une jointure
        if not self.registration.is_regular:
            raise ValidationError(
                "Une annulation future ne peut être réalisée que pour une inscription régulière"
            )

    class Meta:
        verbose_name = "annulation inscription régulière future"
        verbose_name_plural = "annulations inscriptions régulières futures"
        constraints = [
            models.UniqueConstraint(
                "registration",
                "year",
                "week",
                name="unique_future_cancelled_regular_registration_for_one_week",
            ),
        ]


class GlobalSetting(models.Model):
    CURRENT_YEAR = "CURRENT_YEAR"
    CURRENT_WEEK = "CURRENT_WEEK"
    TYPE = {
        "str": "String",
        "int": "Integer",
        "bool": "Boolean",
        "float": "Float",
    }

    key = models.CharField("Clé", max_length=255, unique=True)
    value = models.TextField("Valeur")
    value_type = models.CharField("Type", max_length=10, choices=TYPE, default="str")

    def __str__(self):
        return f"{self.key}: {self.value_type} = {self.value}"

    class Meta:
        verbose_name = "paramètre global"
        verbose_name_plural = "paramètres globaux"

    @classmethod
    def get_value(cls, key: str, default=None):
        try:
            setting = cls.objects.get(key=key)
            if setting.value_type == "bool":
                return setting.value.lower() == "true"
            elif setting.value_type == "int":
                return int(setting.value)
            elif setting.value_type == "float":
                return float(setting.value)
            # String by default
            return setting.value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_value(cls, key: str, value, value_type: str = "str"):
        setting, _ = cls.objects.get_or_create(key=key)
        setting.value = str(value)
        setting.value_type = value_type
        setting.save()

    @classmethod
    def get_year(cls) -> int:
        return cls.get_value(cls.CURRENT_YEAR)

    @classmethod
    def set_year(cls, year: int):
        cls.set_value(cls.CURRENT_YEAR, year, "int")

    @classmethod
    def get_week(cls) -> int:
        return cls.get_value(cls.CURRENT_WEEK)

    @classmethod
    def set_week(cls, week: int):
        cls.set_value(cls.CURRENT_WEEK, week, "int")
