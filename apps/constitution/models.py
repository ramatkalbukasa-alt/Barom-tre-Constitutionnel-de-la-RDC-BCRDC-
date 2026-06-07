from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from pgvector.django import VectorField, HnswIndex


class THEME:
    SOUVERAINETE = "souverainete"
    DROITS_FONDAMENTAUX = "droits_fondamentaux"
    POUVOIR_EXECUTIF = "pouvoir_executif"
    POUVOIR_LEGISLATIF = "pouvoir_legislatif"
    POUVOIR_JUDICIAIRE = "pouvoir_judiciaire"
    ORGANISATION_TERRITORIALE = "organisation_territoriale"
    JUSTICE_CONSTITUTIONNELLE = "justice_constitutionnelle"
    FINANCES_PUBLIQUES = "finances_publiques"
    FORCE_ARMEE = "force_armee"
    REVISION = "revision"
    DISPOSITIONS_FINALES = "dispositions_finales"
    AUTRE = "autre"

    CHOICES = [
        (SOUVERAINETE, "Souveraineté & État"),
        (DROITS_FONDAMENTAUX, "Droits & Libertés Fondamentaux"),
        (POUVOIR_EXECUTIF, "Pouvoir Exécutif"),
        (POUVOIR_LEGISLATIF, "Pouvoir Législatif"),
        (POUVOIR_JUDICIAIRE, "Pouvoir Judiciaire"),
        (ORGANISATION_TERRITORIALE, "Organisation Territoriale"),
        (JUSTICE_CONSTITUTIONNELLE, "Justice Constitutionnelle"),
        (FINANCES_PUBLIQUES, "Finances Publiques"),
        (FORCE_ARMEE, "Forces Armées & Sécurité"),
        (REVISION, "Révision Constitutionnelle"),
        (DISPOSITIONS_FINALES, "Dispositions Finales"),
        (AUTRE, "Autre"),
    ]

    ICONS = {
        SOUVERAINETE: "🏛️",
        DROITS_FONDAMENTAUX: "🤝",
        POUVOIR_EXECUTIF: "👤",
        POUVOIR_LEGISLATIF: "🏛️",
        POUVOIR_JUDICIAIRE: "⚖️",
        ORGANISATION_TERRITORIALE: "🗺️",
        JUSTICE_CONSTITUTIONNELLE: "📜",
        FINANCES_PUBLIQUES: "💰",
        FORCE_ARMEE: "🛡️",
        REVISION: "✏️",
        DISPOSITIONS_FINALES: "📋",
        AUTRE: "📄",
    }


class ConstitutionArticle(models.Model):
    number = models.PositiveSmallIntegerField(
        unique=True,
        verbose_name="Numéro d'article",
        db_index=True,
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Titre",
    )
    content = models.TextField(verbose_name="Contenu")
    theme = models.CharField(
        max_length=50,
        choices=THEME.CHOICES,
        default=THEME.AUTRE,
        verbose_name="Thème",
        db_index=True,
    )
    keywords = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Mots-clés",
    )
    search_vector = SearchVectorField(null=True, blank=True)
    embedding = VectorField(
        dimensions=1536,
        null=True,
        blank=True,
        verbose_name="Embedding vectoriel",
        help_text="Vecteur OpenAI text-embedding-3-small (1536 dims)",
    )
    language = models.CharField(
        max_length=10,
        default="fr",
        verbose_name="Langue",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Article constitutionnel"
        verbose_name_plural = "Articles constitutionnels"
        ordering = ["number"]
        indexes = [
            GinIndex(fields=["search_vector"], name="article_search_vector_idx"),
            HnswIndex(
                name="article_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self):
        return f"Art. {self.number} — {self.title or 'Sans titre'}"

    @property
    def theme_icon(self) -> str:
        return THEME.ICONS.get(self.theme, "📄")

    @property
    def short_content(self) -> str:
        return self.content[:300] + "…" if len(self.content) > 300 else self.content
