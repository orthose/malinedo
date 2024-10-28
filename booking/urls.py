from django.urls import path

from . import views

urlpatterns = [
    path("home/", views.home, name="home"),
    path("edit/", views.edit, name="edit"),
    path("notice/", views.notice, name="notice"),
]
