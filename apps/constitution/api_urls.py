from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework import viewsets
from .models import ConstitutionArticle
from .serializers import ConstitutionArticleSerializer

app_name = "constitution_api"


class ConstitutionArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ConstitutionArticle.objects.all()
    serializer_class = ConstitutionArticleSerializer
    search_fields = ["number", "title", "content"]

    def get_queryset(self):
        qs = super().get_queryset()
        theme = self.request.query_params.get("theme")
        if theme:
            qs = qs.filter(theme=theme)
        return qs


router = DefaultRouter()
router.register(r"articles", ConstitutionArticleViewSet, basename="article")

urlpatterns = router.urls
