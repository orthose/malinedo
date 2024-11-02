from django import forms
from django.db.models import TextChoices
from crispy_forms.helper import FormHelper
from django.contrib.auth.models import AbstractUser

from .models import ClubGroup, RegisterPermission


class ScheduleForm(forms.Form):
    class SessionFilter(TextChoices):
        MY = "my", "Mes inscriptions"
        ALL = "all", "Toutes"

    class GroupFilter(TextChoices):
        ALL = "A", "Tous"
        LEISURE = "L", ClubGroup.LEISURE
        YOUNG = "J", ClubGroup.YOUNG
        COMPET_N1 = "C1", ClubGroup.COMPET_N1
        COMPET_N2 = "C2", ClubGroup.COMPET_N2

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

    def filter_group_choices(self, user: AbstractUser):
        choices = [
            (group, verbose_name)
            for group, verbose_name in self.fields["group"].choices
            if group == self.GroupFilter.ALL
            or user.has_perm(RegisterPermission.get_perm(group))
        ]
        self.fields["group"] = forms.ChoiceField(label="Groupe", choices=choices)


class EditSessionRegistrationForm(forms.Form):
    session_id = forms.IntegerField(label="Session", required=True)
    is_regular = forms.BooleanField(label="Régulière ?", required=False)
    # Annuler une inscription
    is_cancelled = forms.BooleanField(label="Annulée ?", required=False)
    swimmer_is_coach = forms.BooleanField(label="Entraîneur ?", required=False)
    # Supprimer une inscription régulière
    remove = forms.BooleanField(label="Supprimer ?", required=False)
