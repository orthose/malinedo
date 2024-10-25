import datetime
from enum import Enum
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


def get_anonymous_user() -> AbstractUser:
    return get_user_model().objects.get_or_create(username="Anonyme")[0]


def get_current_year() -> int:
    return datetime.date.today().year


def get_year_field() -> models.Field:
    return models.IntegerField("année")


def get_current_week() -> int:
    return datetime.date.today().isocalendar().week


def get_week_field() -> models.Field:
    return models.PositiveSmallIntegerField(
        "semaine",
        validators=[
            MinValueValidator(1),
            MaxValueValidator(53),
        ],
    )


class ClubGroups(Enum):
    BOARD = "Bureau"
    COACH = "Entraîneur"
    YOUNG = "Jeune"
    LEISURE = "Loisir"
    COMPET = "Compétition"


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

    GROUP = {
        "J": ClubGroups.YOUNG.value,
        "L": ClubGroups.LEISURE.value,
        "C": ClubGroups.COMPET.value,
    }

    group = models.CharField("Groupe", max_length=1, choices=GROUP)
    weekday = models.PositiveSmallIntegerField("Jour", choices=WEEKDAY)
    start_hour = models.TimeField("Heure début")
    stop_hour = models.TimeField("Heure fin")
    capacity = models.PositiveSmallIntegerField("Capacité")
    is_cancelled = models.BooleanField("Est annulée ?", default=False)

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
    def swimmers(self) -> list[AbstractUser]:
        pass

    @property
    def coaches(self) -> list[AbstractUser]:
        pass

    def __str__(self) -> str:
        return f"[{self.GROUP[self.group]}] {self.WEEKDAY[self.weekday]} {self.start_hour.strftime('%Hh%M')}-{self.stop_hour.strftime('%Hh%M')}"

    def clean(self):
        if self.start_hour >= self.stop_hour:
            raise ValidationError(
                "L'heure de début de séance doit être antérieure à l'heure de fin"
            )

    class Meta:
        abstract = True


class WeeklySession(AbstractWeeklySession):
    """
    Créneaux d'entraînement hebdomadaires statiques définis en début d'année

    L'unicité de chaque créneau est défini par:
        + Groupe de niveau (Loisir, Compétition)
        + Jour de la semaine
        + Heure de début

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
    def swimmers(self) -> list[AbstractUser]:
        return [
            registration.swimmer
            for registration in SessionRegistration.objects.filter(
                session=self,
                is_cancelled=False,
                swimmer_is_coach=False,
            )
        ]

    @property
    def coaches(self) -> list[AbstractUser]:
        return [
            registration.swimmer
            for registration in SessionRegistration.objects.filter(
                session=self, is_cancelled=False, swimmer_is_coach=True
            )
        ]

    def to_history(self, year: int, week: int) -> "WeeklySessionHistory":
        session = self.__dict__.copy()
        session.pop("id")
        session.pop("_state")
        session["year"] = year
        session["week"] = week
        return WeeklySessionHistory(**session)

    class Meta:
        verbose_name = "session hebdomadaire"
        verbose_name_plural = "sessions hebdomadaires"
        constraints = [
            models.UniqueConstraint(
                "group",
                "weekday",
                "start_hour",
                name="unique_weekly_session_hour_per_group",
            ),
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
    def swimmers(self) -> list[AbstractUser]:
        return [
            registration.swimmer
            for registration in SessionRegistrationHistory.objects.filter(
                session=self,
                year=self.year,
                week=self.week,
                is_cancelled=False,
                swimmer_is_coach=False,
            )
        ]

    @property
    def coaches(self) -> list[AbstractUser]:
        return [
            registration.swimmer
            for registration in SessionRegistrationHistory.objects.filter(
                session=self,
                year=self.year,
                week=self.week,
                is_cancelled=False,
                swimmer_is_coach=True,
            )
        ]

    def __str__(self) -> str:
        return f"{self.year}-{self.week} " + super().__str__()

    class Meta:
        verbose_name = "historique session hebdomadaire"
        verbose_name_plural = "historique sessions hebdomadaires"
        constraints = [
            models.UniqueConstraint(
                "group",
                "weekday",
                "start_hour",
                "year",
                "week",
                name="unique_weekly_session_history_hour_per_group",
            ),
            models.CheckConstraint(
                check=models.Q(start_hour__lt=models.F("stop_hour")),
                name="check_weekly_session_history_start_hour_before_stop_hour",
            ),
        ]


class AbstractSessionRegistration(models.Model):
    swimmer = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET(get_anonymous_user),
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
        return f"({self.swimmer.first_name} {self.swimmer.last_name}) {self.session}"

    class Meta:
        abstract = True


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

    def to_history(self, year: int, week: int) -> "SessionRegistrationHistory":
        registration = self.__dict__.copy()
        registration.pop("id")
        registration.pop("_state")
        registration["year"] = year
        registration["week"] = week
        session = WeeklySession.objects.get(pk=registration["session_id"])
        registration["session_id"] = WeeklySessionHistory.objects.get(
            year=get_current_year(),
            week=get_current_week(),
            group=session.group,
            weekday=session.weekday,
            start_hour=session.start_hour,
        ).pk
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
        permissions = [
            (
                "register_coach_session",
                "Le nageur peut s'inscrire en tant qu'entraîneur à une session régulière",
            ),
            (
                "register_leisure_session",
                "Le nageur en loisir peut s'inscrire à une session de loisir régulière",
            ),
            (
                "register_compet_session",
                "Le nageur en compétition peut s'inscrire à une session de compétition régulière",
            ),
        ]


class SessionRegistrationHistory(AbstractSessionRegistration):
    """
    Historique des inscriptions pour les statistiques
    """

    session = models.ForeignKey(
        WeeklySessionHistory,
        on_delete=models.CASCADE,
    )
    year = get_year_field()
    week = get_week_field()

    class Meta:
        verbose_name = "historique inscription session"
        verbose_name_plural = "historique inscriptions sessions"
        constraints = [
            models.UniqueConstraint(
                "swimmer",
                "session",
                "year",
                "week",
                name="unique_swimmer_for_one_session_history",
            ),
        ]
        permissions = []


class GlobalSetting(models.Model):
    CURRENT_YEAR = "CURRENT_YEAR"
    CURRENT_WEEK = "CURRENT_WEEK"
    IS_BOOKING_ACTIVE = "IS_BOOKING_ACTIVE"
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

    @classmethod
    def get_is_booking_active(cls) -> bool:
        return cls.get_value(cls.IS_BOOKING_ACTIVE)

    @classmethod
    def set_is_booking_active(cls, is_active: bool):
        cls.set_value(cls.IS_BOOKING_ACTIVE, is_active, "bool")
