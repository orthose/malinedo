from django.urls import path

from . import views

urlpatterns = [
    path("home/", views.schedule, name="home"),
    path("edit/", views.edit, name="edit"),
    path("groups/", views.groups, name="groups"),
    path("help/", views.help, name="help"),
]
