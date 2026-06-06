from django.contrib import admin
from .models import AIQuery


@admin.register(AIQuery)
class AIQueryAdmin(admin.ModelAdmin):
    list_display = ("id", "question_preview", "language", "tokens_used", "created_at")
    list_filter = ("language",)
    search_fields = ("question", "response_fr")
    readonly_fields = ("question", "language", "response_fr", "response_lingala",
                       "articles_used", "tokens_used", "created_at")
    filter_horizontal = ("articles_used",)

    def question_preview(self, obj):
        return obj.question[:80] + "…" if len(obj.question) > 80 else obj.question
    question_preview.short_description = "Question"
