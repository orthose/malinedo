import datetime
from django.db import models
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

from accounts.models import User


class GlobalState(models.Model):
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

    @classmethod
    def is_current_week(cls, year: int, week: int) -> bool:
        return cls.get_year() == year and cls.get_week() == week

    @classmethod
    def is_future_week(cls, year: int, week: int) -> bool:
        current_year = cls.get_year()
        current_week = cls.get_week()
        return year > current_year or (year == current_year and week > current_week)


class SessionGroup(models.Model):
    """
    Groupe de niveau de nage

    En fonction du groupe auquel un nageur appartient,
    il ne peut pas s'inscrire à plus d'un certain
    nombre de séances par semaine
    """

    name = models.CharField("Nom", max_length=255, unique=True)
    groups = models.ManyToManyField(Group, verbose_name="Groupes")
    max_registrations_per_week = models.PositiveSmallIntegerField(
        verbose_name="Limite d'inscriptions hebdomadaires par nageur",
    )

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = "groupe de nage"
        verbose_name_plural = "groupes de nage"


class WeeklySession(models.Model):
    """
    Séances d'entraînement hebdomadaires définis en début d'année

    L'unicité de chaque séance est définie par:
        + Année
        + Semaine
        + Groupe de niveau (ex: Loisir, Compétition)
        + Jour de la semaine
        + Heure de début

    Les autres champs à compléter pour chaque séance sont:
        + Heure de fin
        + Capacité (nombre de nageurs)

    Les autres champs diponibles pour chaque séance sont:
        + La séance est-elle annulée cette semaine ?
        + Durée de la séance
        + Nombre de nageurs inscrits
        + Taux d'inscriptions
        + Liste des nageurs inscrits
        + Liste des entraîneurs inscrits
    """

    WEEKDAY = {
        1: "Lundi",
        2: "Mardi",
        3: "Mercredi",
        4: "Jeudi",
        5: "Vendredi",
        6: "Samedi",
        7: "Dimanche",
    }

    year = models.IntegerField("année", default=GlobalState.get_year)
    week = models.PositiveSmallIntegerField(
        "semaine",
        validators=[
            MinValueValidator(1),
            MaxValueValidator(53),
        ],
        default=GlobalState.get_week,
    )
    group = models.ForeignKey(
        SessionGroup,
        # Si le groupe est NULL n'importe qui peut s'inscire à la séance
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Groupe",
    )
    weekday = models.PositiveSmallIntegerField("Jour", choices=WEEKDAY)
    start_hour = models.TimeField("Heure début")
    stop_hour = models.TimeField("Heure fin")
    capacity = models.PositiveSmallIntegerField("Capacité")
    is_cancelled = models.BooleanField("Est annulée ?", default=False)

    # Champs construits en mémoire par WeekScheduleQuery
    user_registration: list["SessionRegistration"]
    coach_registrations: list["SessionRegistration"]
    swimmer_registrations: list["SessionRegistration"]

    class Meta:
        verbose_name = "session hebdomadaire"
        verbose_name_plural = "sessions hebdomadaires"
        indexes = [
            models.Index(fields=["year", "week"]),
        ]
        constraints = [
            models.UniqueConstraint(
                "year",
                "week",
                "group",
                "weekday",
                "start_hour",
                name="unique_weekly_session_hour_per_group",
            ),
            models.CheckConstraint(
                condition=models.Q(start_hour__lt=models.F("stop_hour")),
                name="check_weekly_session_start_hour_before_stop_hour",
            ),
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
        return len(self.swimmer_registrations)

    @property
    def registration_rate(self) -> int:
        return round(self.total_swimmers * 100 / self.capacity)

    @property
    def french_weekday(self) -> str:
        return self.WEEKDAY[self.weekday]

    @property
    def french_date(self) -> str:
        return datetime.datetime.fromisocalendar(
            self.year,
            self.week,
            self.weekday,
        ).strftime("%d/%m/%Y")

    def __str__(self) -> str:
        group_name = self.group.name if self.group is not None else "Aucun"
        return f"{self.year}-{self.week} [{group_name}] {self.WEEKDAY[self.weekday]} {self.start_hour.strftime('%Hh%M')}-{self.stop_hour.strftime('%Hh%M')}"

    def clean(self):
        if self.start_hour >= self.stop_hour:
            raise ValidationError(
                "L'heure de début de séance doit être antérieure à l'heure de fin"
            )

        # Si on crée une séance pour une semaine future
        # il faut qu'elle existe dans le semaine courante
        if (
            GlobalState.is_future_week(self.year, self.week)
            and not self.__class__.objects.filter(
                year=GlobalState.get_year(),
                week=GlobalState.get_week(),
                group=self.group,
                weekday=self.weekday,
                start_hour=self.start_hour,
            ).exists()
        ):
            raise ValidationError(
                "La séance future ne peut pas être créée car elle n'existe pas pour la semaine courante"
            )

    def delete(self, *args, **kwargs):
        # Si on supprime une séance de la semaine courante
        # il faut supprimer les séances futures associées
        if GlobalState.is_current_week(self.year, self.week):
            current_year = GlobalState.get_year()
            current_week = GlobalState.get_week()
            self.__class__.objects.filter(
                group=self.group,
                weekday=self.weekday,
                start_hour=self.start_hour,
            ).filter(
                models.Q(year__gt=current_year)
                | models.Q(year=current_year, week__gt=current_week)
            ).delete()

        return super().delete(*args, **kwargs)


class SessionRegistration(models.Model):
    """
    Inscription des nageurs aux entraînements de la semaine

    L'unicité de chaque inscription est définie par:
        + Nageur
        + Séance

    Ainsi un nageur ne peut pas s'inscrire deux fois à la même séance

    Les autres champs à compléter pour chaque inscription sont:
        + Est-ce la séance d'inscription habituelle du nageur ?
        + Le nageur a-t-il annulé son inscription cette semaine ?
        + Le nageur est-il l'entraîneur de la séance ?
    """

    swimmer = models.ForeignKey(
        User,
        # La logique de suppression des inscriptions en fonction de la semaine
        # est dans accounts/models/User.delete et s'exécute avant le on_delete
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

    def __str__(self) -> str:
        return f"({self.swimmer.first_name} {self.swimmer.last_name.upper()}) {self.session}"

    def clean(self):
        # Si le nageur veut s'inscrire en tant qu'entraîneur en a-t-il la permission ?
        if self.swimmer_is_coach and not self.swimmer.is_coach:
            raise ValidationError(
                "Le nageur n'a pas la permission de s'inscrire en tant qu'entraîneur"
            )

        # Si le nageur ou l'entraîneur veut s'inscrire en a-t-il la permission en fonction de ses groupes ?
        if (
            self.session.group is not None
            and not self.swimmer.groups.filter(
                pk__in=self.session.group.groups.values("pk")
            ).exists()
        ):
            raise ValidationError(
                "Le nageur ne peut pas s'inscrire car il n'est pas dans le groupe de la séance"
            )

        # Si le nageur veut s'inscrire a-t-il déjà un entraînement prévu à la même heure ?
        if (
            not self.swimmer_is_coach
            and self.__class__.objects.exclude(pk=self.pk)
            .filter(
                swimmer=self.swimmer,
                session__year=self.session.year,
                session__week=self.session.week,
                session__weekday=self.session.weekday,
                session__start_hour=self.session.start_hour,
            )
            .exists()
        ):
            raise ValidationError(
                "Le nageur ne peut pas s'inscrire car il a déjà un entraînement prévu à la même heure"
            )

        # Un nageur ne peut pas s'inscrire à une séance future
        # mais seulement annuler dans le futur une inscription régulière
        if not (
            not self.swimmer_is_coach and self.is_regular and self.is_cancelled
        ) and GlobalState.is_future_week(self.session.year, self.session.week):
            raise ValidationError(
                "Un nageur ne peut pas s'inscrire à une séance future"
            )
