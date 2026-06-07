import pgvector.django
from pgvector.django import VectorExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("constitution", "0002_search_vector_trigger"),
    ]

    operations = [
        # Enable the pgvector extension (CREATE EXTENSION IF NOT EXISTS vector).
        VectorExtension(),
        # The old column was a JSON array; there is no safe in-place cast to the
        # native `vector` type, so we drop and recreate it. Embeddings must be
        # regenerated with scripts/generate_embeddings.py after this migration.
        migrations.RemoveField(
            model_name="constitutionarticle",
            name="embedding",
        ),
        migrations.AddField(
            model_name="constitutionarticle",
            name="embedding",
            field=pgvector.django.VectorField(
                blank=True,
                dimensions=1536,
                help_text="Vecteur OpenAI text-embedding-3-small (1536 dims)",
                null=True,
                verbose_name="Embedding vectoriel",
            ),
        ),
        migrations.AddIndex(
            model_name="constitutionarticle",
            index=pgvector.django.HnswIndex(
                ef_construction=64,
                fields=["embedding"],
                m=16,
                name="article_embedding_hnsw",
                opclasses=["vector_cosine_ops"],
            ),
        ),
    ]
