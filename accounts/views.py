from typing import cast
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required

from accounts.models import User
from accounts.forms import EditUserSettings


@login_required
def user_settings(request: HttpRequest) -> HttpResponse:
    request.user = cast(User, request.user)

    form = EditUserSettings({"enable_notifications": request.user.enable_notifications})

    if request.method == "POST":
        form = EditUserSettings(request.POST)

        if form.is_valid():
            request.user.enable_notifications = form.cleaned_data[
                "enable_notifications"
            ]
            request.user.save()

    # Attributs HTML pour les champs de formulaire du template
    form.fields["enable_notifications"].widget.attrs.update(
        {
            "class": "btn-check",
            "autocomplete": "off",
            # Soumission automatique du formulaire
            "onclick": "this.form.submit()",
        }
    )

    context = {"form": form}
    return render(request, "settings/user_settings.html", context)
