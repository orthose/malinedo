from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User

class CustomUserAdmin(UserAdmin):
    # Définir les champs à afficher dans la liste
    list_display = ('username', 'first_name', 'last_name', 'is_staff')

admin.site.register(User, CustomUserAdmin)
