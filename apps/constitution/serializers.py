from rest_framework import serializers
from .models import ConstitutionArticle


class ConstitutionArticleSerializer(serializers.ModelSerializer):
    theme_display = serializers.CharField(source="get_theme_display", read_only=True)
    theme_icon = serializers.CharField(read_only=True)

    class Meta:
        model = ConstitutionArticle
        fields = ["id", "number", "title", "content", "theme", "theme_display", "theme_icon", "keywords", "language"]
