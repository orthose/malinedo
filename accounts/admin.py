from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


class CustomUserAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "is_staff")


def clean(self):
    username = self.cleaned_data.get("username")
    self.cleaned_data["email"] = username
    return self.cleaned_data


# Monkey patch pour forcer email = username
# depuis le formulaire administrateur
CustomUserAdmin.form.clean = clean


admin.site.register(User, CustomUserAdmin)
