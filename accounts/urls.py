# from django.contrib.auth import views as auth_views
from django.urls import include, path


urlpatterns = [
    path("accounts/", include("django.contrib.auth.urls")),
    # path("login/", auth_views.LoginView.as_view()),
]