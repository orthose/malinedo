# Generated by Django 5.1.2 on 2024-10-28 09:00

import booking.models
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GlobalSetting",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "key",
                    models.CharField(max_length=255, unique=True, verbose_name="Clé"),
                ),
                ("value", models.TextField(verbose_name="Valeur")),
                (
                    "value_type",
                    models.CharField(
                        choices=[
                            ("str", "String"),
                            ("int", "Integer"),
                            ("bool", "Boolean"),
                            ("float", "Float"),
                        ],
                        default="str",
                        max_length=10,
                        verbose_name="Type",
                    ),
                ),
            ],
            options={
                "verbose_name": "paramètre global",
                "verbose_name_plural": "paramètres globaux",
            },
        ),
        migrations.CreateModel(
            name="WeeklySession",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "group",
                    models.CharField(
                        choices=[
                            ("L", "Loisir"),
                            ("J", "Jeune"),
                            ("C1", "Compétition N1"),
                            ("C2", "Compétition N2"),
                        ],
                        max_length=2,
                        verbose_name="Groupe",
                    ),
                ),
                (
                    "weekday",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Lundi"),
                            (2, "Mardi"),
                            (3, "Mercredi"),
                            (4, "Jeudi"),
                            (5, "Vendredi"),
                            (6, "Samedi"),
                            (7, "Dimanche"),
                        ],
                        verbose_name="Jour",
                    ),
                ),
                ("start_hour", models.TimeField(verbose_name="Heure début")),
                ("stop_hour", models.TimeField(verbose_name="Heure fin")),
                ("capacity", models.PositiveSmallIntegerField(verbose_name="Capacité")),
                (
                    "is_cancelled",
                    models.BooleanField(default=False, verbose_name="Est annulée ?"),
                ),
            ],
            options={
                "verbose_name": "session hebdomadaire",
                "verbose_name_plural": "sessions hebdomadaires",
                "constraints": [
                    models.UniqueConstraint(
                        models.F("group"),
                        models.F("weekday"),
                        models.F("start_hour"),
                        name="unique_weekly_session_hour_per_group",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("start_hour__lt", models.F("stop_hour"))),
                        name="check_weekly_session_start_hour_before_stop_hour",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="WeeklySessionHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "group",
                    models.CharField(
                        choices=[
                            ("L", "Loisir"),
                            ("J", "Jeune"),
                            ("C1", "Compétition N1"),
                            ("C2", "Compétition N2"),
                        ],
                        max_length=2,
                        verbose_name="Groupe",
                    ),
                ),
                (
                    "weekday",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Lundi"),
                            (2, "Mardi"),
                            (3, "Mercredi"),
                            (4, "Jeudi"),
                            (5, "Vendredi"),
                            (6, "Samedi"),
                            (7, "Dimanche"),
                        ],
                        verbose_name="Jour",
                    ),
                ),
                ("start_hour", models.TimeField(verbose_name="Heure début")),
                ("stop_hour", models.TimeField(verbose_name="Heure fin")),
                ("capacity", models.PositiveSmallIntegerField(verbose_name="Capacité")),
                (
                    "is_cancelled",
                    models.BooleanField(default=False, verbose_name="Est annulée ?"),
                ),
                ("year", models.IntegerField(verbose_name="année")),
                (
                    "week",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(53),
                        ],
                        verbose_name="semaine",
                    ),
                ),
            ],
            options={
                "verbose_name": "historique session hebdomadaire",
                "verbose_name_plural": "historique sessions hebdomadaires",
                "constraints": [
                    models.UniqueConstraint(
                        models.F("group"),
                        models.F("weekday"),
                        models.F("start_hour"),
                        models.F("year"),
                        models.F("week"),
                        name="unique_weekly_session_history_hour_per_group",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("start_hour__lt", models.F("stop_hour"))),
                        name="check_weekly_session_history_start_hour_before_stop_hour",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="SessionRegistration",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("is_regular", models.BooleanField(verbose_name="Est régulière ?")),
                (
                    "is_cancelled",
                    models.BooleanField(default=False, verbose_name="Est annulée ?"),
                ),
                (
                    "swimmer_is_coach",
                    models.BooleanField(default=False, verbose_name="Est entraîneur ?"),
                ),
                (
                    "swimmer",
                    models.ForeignKey(
                        on_delete=models.SET(booking.models.get_anonymous_user),
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Nageur",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="booking.weeklysession",
                        verbose_name="Session",
                    ),
                ),
            ],
            options={
                "verbose_name": "inscription session",
                "verbose_name_plural": "inscriptions sessions",
                "permissions": [
                    (
                        "register_coach_session",
                        "Le nageur peut s'inscrire en tant qu'entraîneur à une session",
                    ),
                    (
                        "register_leisure_session",
                        "Le nageur en loisir peut s'inscrire à une session de loisir",
                    ),
                    (
                        "register_young_session",
                        "Le jeune nageur peut s'inscrire à une session de jeune",
                    ),
                    (
                        "register_competn1_session",
                        "Le nageur en compétition peut s'inscrire à une session de compétition de niveau 1",
                    ),
                    (
                        "register_competn2_session",
                        "Le nageur en compétition peut s'inscrire à une session de compétition de niveau 2",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        models.F("swimmer"),
                        models.F("session"),
                        name="unique_swimmer_for_one_session",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="SessionRegistrationHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("is_regular", models.BooleanField(verbose_name="Est régulière ?")),
                (
                    "is_cancelled",
                    models.BooleanField(default=False, verbose_name="Est annulée ?"),
                ),
                (
                    "swimmer_is_coach",
                    models.BooleanField(default=False, verbose_name="Est entraîneur ?"),
                ),
                ("year", models.IntegerField(verbose_name="année")),
                (
                    "week",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(53),
                        ],
                        verbose_name="semaine",
                    ),
                ),
                (
                    "swimmer",
                    models.ForeignKey(
                        on_delete=models.SET(booking.models.get_anonymous_user),
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Nageur",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="booking.weeklysessionhistory",
                    ),
                ),
            ],
            options={
                "verbose_name": "historique inscription session",
                "verbose_name_plural": "historique inscriptions sessions",
                "permissions": [],
                "constraints": [
                    models.UniqueConstraint(
                        models.F("swimmer"),
                        models.F("session"),
                        models.F("year"),
                        models.F("week"),
                        name="unique_swimmer_for_one_session_history",
                    )
                ],
            },
        ),
    ]
