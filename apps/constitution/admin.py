from django.contrib import admin
from .models import ConstitutionArticle


@admin.register(ConstitutionArticle)
class ConstitutionArticleAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "theme", "has_embedding", "created_at")
    list_filter = ("theme", "language")
    search_fields = ("number", "title", "content", "keywords")
    readonly_fields = ("search_vector", "embedding", "created_at", "updated_at")
    ordering = ("number",)

    fieldsets = (
        (None, {"fields": ("number", "title", "content")}),
        ("Classification", {"fields": ("theme", "keywords", "language")}),
        ("IA", {"fields": ("embedding", "search_vector"), "classes": ("collapse",)}),
        ("Dates", {"fields": ("created_at", "updated_at")}),
    )

    def has_embedding(self, obj):
        return obj.embedding is not None
    has_embedding.boolean = True
    has_embedding.short_description = "Embedding IA"
