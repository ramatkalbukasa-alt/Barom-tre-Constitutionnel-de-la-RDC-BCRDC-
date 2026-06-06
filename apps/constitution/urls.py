from django.urls import path
from . import views

app_name = "constitution"

urlpatterns = [
    path("", views.article_list, name="list"),
    path("article/<int:number>/", views.article_detail, name="detail"),
    path("recherche/", views.article_search_htmx, name="search_htmx"),
]
