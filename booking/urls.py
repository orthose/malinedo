from django.urls import path

from . import views

urlpatterns = [
    path("home/", views.schedule, {"show_history_filters": False}, name="home"),
    path("history/", views.schedule, {"show_history_filters": True}, name="history"),
    path("edit/", views.edit, name="edit"),
    path("notice/", views.notice, name="notice"),
]
