from django import forms
from django.db.models import TextChoices
from crispy_forms.helper import FormHelper

from .models import ClubGroups, GlobalSetting


class ScheduleForm(forms.Form):
    class SessionFilter(TextChoices):
        MY = "my", "Mes inscriptions"
        ALL = "all", "Toutes"

    class GroupFilter(TextChoices):
        ALL = "A", "Tous"
        YOUNG = "J", ClubGroups.YOUNG.value
        LEISURE = "L", ClubGroups.LEISURE.value
        COMPET = "C", ClubGroups.COMPET.value

    sessions = forms.ChoiceField(label="Séances", choices=SessionFilter)
    group = forms.ChoiceField(label="Groupe", choices=GroupFilter)
    year = forms.IntegerField(
        label="Année",
        min_value=-9999,
        max_value=9999,
    )
    week = forms.IntegerField(
        label="Semaine",
        min_value=1,
        max_value=53,
    )

    # Crispy
    helper = FormHelper()
    helper.form_show_labels = False
