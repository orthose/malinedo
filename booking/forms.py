from django import forms


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
    session_id = forms.IntegerField(label="Session", required=True)
    is_regular = forms.BooleanField(label="Régulière ?", required=False)
    # Annuler une inscription
    is_cancelled = forms.BooleanField(label="Annulée ?", required=False)
    swimmer_is_coach = forms.BooleanField(label="Entraîneur ?", required=False)
    # Supprimer une inscription
    remove = forms.BooleanField(label="Supprimer ?", required=False)
