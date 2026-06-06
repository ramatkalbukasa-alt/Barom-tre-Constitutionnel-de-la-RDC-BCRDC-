from django.db import models
from django.conf import settings


class VOTE_CHOICE:
    MAINTIEN = "maintien"
    REVISION = "revision"
    CHANGEMENT = "changement"

    CHOICES = [
        (MAINTIEN, "Maintien de la Constitution actuelle"),
        (REVISION, "Révision partielle de la Constitution"),
        (CHANGEMENT, "Changement complet de la Constitution"),
    ]

    COLORS = {
        MAINTIEN: "#16A34A",
        REVISION: "#D97706",
        CHANGEMENT: "#DC2626",
    }

    ICONS = {
        MAINTIEN: "shield-check",
        REVISION: "pencil",
        CHANGEMENT: "refresh-cw",
    }


class ARGUMENT_CATEGORY:
    JURIDIQUE = "juridique"
    POLITIQUE = "politique"
    EMOTIONNEL = "emotionnel"
    SOCIOECONOMIQUE = "socioeconomique"
    NON_CLASSE = "non_classe"

    CHOICES = [
        (JURIDIQUE, "Juridique (basé sur articles)"),
        (POLITIQUE, "Politique"),
        (EMOTIONNEL, "Émotionnel"),
        (SOCIOECONOMIQUE, "Socio-économique"),
        (NON_CLASSE, "Non classé"),
    ]


class Vote(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vote",
        verbose_name="Citoyen",
    )
    choice = models.CharField(
        max_length=20,
        choices=VOTE_CHOICE.CHOICES,
        verbose_name="Choix",
        db_index=True,
    )
    justification = models.TextField(
        verbose_name="Justification",
        max_length=2000,
        help_text="Maximum 2000 caractères",
    )
    argument_category = models.CharField(
        max_length=20,
        choices=ARGUMENT_CATEGORY.CHOICES,
        default=ARGUMENT_CATEGORY.NON_CLASSE,
        verbose_name="Catégorie d'argument (IA)",
        db_index=True,
    )
    cited_articles = models.ManyToManyField(
        "constitution.ConstitutionArticle",
        blank=True,
        related_name="votes_citing",
        verbose_name="Articles cités",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vote"
        verbose_name_plural = "Votes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Vote #{self.pk} — {self.get_choice_display()}"


class VoteStatSnapshot(models.Model):
    """Cached statistics snapshot, refreshed periodically by Celery."""
    total_votes = models.PositiveIntegerField(default=0)
    maintien_count = models.PositiveIntegerField(default=0)
    revision_count = models.PositiveIntegerField(default=0)
    changement_count = models.PositiveIntegerField(default=0)
    stats_by_province = models.JSONField(default=dict)
    stats_by_location = models.JSONField(default=dict)
    stats_by_age = models.JSONField(default=dict)
    stats_by_gender = models.JSONField(default=dict)
    stats_by_argument = models.JSONField(default=dict)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Snapshot statistiques"
        verbose_name_plural = "Snapshots statistiques"

    def __str__(self):
        return f"Snapshot {self.computed_at} — {self.total_votes} votes"
