from django.contrib import admin
from .models import Vote, VoteStatSnapshot


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "choice", "argument_category", "has_citations", "created_at")
    list_filter = ("choice", "argument_category", "user__location_type", "user__province")
    search_fields = ("justification",)
    readonly_fields = ("user", "created_at")
    filter_horizontal = ("cited_articles",)
    ordering = ("-created_at",)

    def has_citations(self, obj):
        return obj.cited_articles.exists()
    has_citations.boolean = True
    has_citations.short_description = "Articles cités"


@admin.register(VoteStatSnapshot)
class VoteStatSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "total_votes", "maintien_count", "revision_count", "changement_count", "computed_at")
    readonly_fields = ("total_votes", "maintien_count", "revision_count", "changement_count",
                       "stats_by_province", "stats_by_location", "stats_by_age",
                       "stats_by_gender", "stats_by_argument", "computed_at")
