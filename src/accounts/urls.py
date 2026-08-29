from django.urls import include, path

from . import views


urlpatterns = [
    path("accounts/", include("django.contrib.auth.urls")),
    path("user_settings/", view=views.user_settings, name="user_settings"),
]
