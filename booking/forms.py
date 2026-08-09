import datetime
from django import forms

from .models import GlobalState


class ScheduleForm(forms.Form):
    mysessions = forms.BooleanField(label="Mes séances", required=False)
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


class EditSessionRegistrationForm(forms.Form):
    year = forms.IntegerField(label="Année", required=True)
    week = forms.IntegerField(label="Semaine", required=True)
    session_id = forms.IntegerField(label="Session", required=True)
    is_regular = forms.BooleanField(label="Régulière ?", required=False)
    # Annuler une inscription
    is_cancelled = forms.BooleanField(label="Annulée ?", required=False)
    swimmer_is_coach = forms.BooleanField(label="Entraîneur ?", required=False)
    # Supprimer une inscription
    remove = forms.BooleanField(label="Supprimer ?", required=False)


class AdminCancelFutureSessionsForm(forms.Form):
    start_date = forms.DateField(
        label="Date de début",
        widget=forms.DateInput(attrs={"type": "date", "class": "vDateField"}),
    )
    stop_date = forms.DateField(
        label="Date de fin",
        widget=forms.DateInput(attrs={"type": "date", "class": "vDateField"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date: datetime.date = cleaned_data.get("start_date")
        stop_date: datetime.date = cleaned_data.get("stop_date")

        if not (start_date <= stop_date):
            raise forms.ValidationError(
                "La date de début doit être antérieure ou égale à la date de fin"
            )

        start_date_cal = start_date.isocalendar()
        if GlobalState.is_past_week(start_date_cal.year, start_date_cal.week):
            raise forms.ValidationError(
                "La date de début doit être postérieure ou égale à la semaine courante"
            )

        return cleaned_data
