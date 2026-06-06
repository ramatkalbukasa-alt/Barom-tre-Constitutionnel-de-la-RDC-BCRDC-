from django.db import models


class LANGUAGE:
    FR = "fr"
    LINGALA = "lingala"
    KIKONGO = "kikongo"
    TSHILUBA = "tshiluba"

    CHOICES = [
        (FR, "Français"),
        (LINGALA, "Lingala"),
        (KIKONGO, "Kikongo"),
        (TSHILUBA, "Tshiluba"),
    ]


class AIQuery(models.Model):
    question = models.TextField(verbose_name="Question posée")
    language = models.CharField(
        max_length=10,
        choices=LANGUAGE.CHOICES,
        default=LANGUAGE.FR,
        verbose_name="Langue",
    )
    response_fr = models.TextField(blank=True, verbose_name="Réponse (FR)")
    response_lingala = models.TextField(blank=True, verbose_name="Réponse (Lingala)")
    articles_used = models.ManyToManyField(
        "constitution.ConstitutionArticle",
        blank=True,
        related_name="ai_queries",
        verbose_name="Articles utilisés",
    )
    tokens_used = models.PositiveIntegerField(default=0, verbose_name="Tokens consommés")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Requête IA"
        verbose_name_plural = "Requêtes IA"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Q: {self.question[:60]}…"
