from django.urls import path
from . import views

app_name = "consultation"

urlpatterns = [
    path("voter/", views.vote, name="vote"),
    path("merci/", views.thank_you, name="thank_you"),
    path("tableau-de-bord/", views.dashboard, name="dashboard"),
    path("stats/", views.dashboard_stats_htmx, name="stats_htmx"),
]
