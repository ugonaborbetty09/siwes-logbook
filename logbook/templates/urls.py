from django.urls import path
from logbook import views

urlpatterns = [
    path("", views.home, name="home"),
    path("add-activity/", views.add_activity, name="add_activity"),
]