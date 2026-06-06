from django.urls import path
from . import views

app_name = "ai_engine"

urlpatterns = [
    path("", views.ask_view, name="ask"),
    path("repondre/", views.ask_htmx, name="ask_htmx"),
]
