"""
Génère les embeddings OpenAI pour tous les articles constitutionnels.

Usage:
    python scripts/generate_embeddings.py
    python scripts/generate_embeddings.py --force   # Re-génère même si embedding existant
"""
import os
import sys
import time
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from apps.constitution.models import ConstitutionArticle
from apps.ai_engine.rag import embed_text


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-génère tous les embeddings.")
    args = parser.parse_args()

    qs = ConstitutionArticle.objects.all() if args.force else ConstitutionArticle.objects.filter(embedding=None)
    total = qs.count()

    if total == 0:
        print("Tous les articles ont déjà des embeddings. Utilisez --force pour régénérer.")
        return

    print(f"Génération d'embeddings pour {total} articles…")

    for i, article in enumerate(qs, 1):
        try:
            text = f"Article {article.number}: {article.title}\n{article.content}"
            article.embedding = embed_text(text)
            article.save(update_fields=["embedding"])
            print(f"  [{i:3d}/{total}] Art. {article.number} ✅")
            if i % 20 == 0:
                time.sleep(1)
        except Exception as e:
            print(f"  [{i:3d}/{total}] Art. {article.number} ❌ {e}")
            time.sleep(5)

    print(f"\n✅ {total} embeddings générés.")


if __name__ == "__main__":
    main()
