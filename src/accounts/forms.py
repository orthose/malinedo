from django import forms


class EditUserSettings(forms.Form):
    enable_notifications = forms.BooleanField(label="Notifications", required=False)
