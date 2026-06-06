from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework import viewsets
from .models import ConstitutionArticle
from .serializers import ConstitutionArticleSerializer

app_name = "constitution_api"


class ConstitutionArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ConstitutionArticle.objects.all()
    serializer_class = ConstitutionArticleSerializer
    filterset_fields = ["theme", "language"]
    search_fields = ["number", "title", "content"]


router = DefaultRouter()
router.register(r"articles", ConstitutionArticleViewSet, basename="article")

urlpatterns = router.urls
