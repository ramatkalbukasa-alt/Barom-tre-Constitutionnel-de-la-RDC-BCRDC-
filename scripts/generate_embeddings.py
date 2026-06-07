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


def _is_fatal_error(exc: Exception) -> bool:
    """Stop the batch on billing/auth errors — retrying 229 times wastes time."""
    msg = str(exc).lower()
    return (
        "insufficient_quota" in msg
        or "invalid_api_key" in msg
        or "incorrect api key" in msg
        or "api key not valid" in msg
        or "permission_denied" in msg
    )


def _is_rate_limit(exc: Exception) -> bool:
    """Transient rate-limit error (Gemini/OpenAI free tier) — worth retrying."""
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "resource_exhausted" in msg or "quota exceeded" in msg


def _embed_with_retry(text: str, max_retries: int = 5) -> list:
    """Embed a single text, retrying with backoff on rate-limit errors."""
    delay = 5
    for attempt in range(max_retries):
        try:
            return embed_text(text)
        except Exception as e:
            if _is_rate_limit(e) and attempt < max_retries - 1:
                print(f"      ⏳ Limite de débit — nouvelle tentative dans {delay}s…")
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise


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
    ok = 0

    for i, article in enumerate(qs, 1):
        try:
            text = f"Article {article.number}: {article.title}\n{article.content}"
            article.embedding = _embed_with_retry(text)
            article.save(update_fields=["embedding"])
            ok += 1
            print(f"  [{i:3d}/{total}] Art. {article.number} ✅")
            # Espacement doux pour rester sous la limite du palier gratuit.
            time.sleep(0.5)
        except Exception as e:
            print(f"  [{i:3d}/{total}] Art. {article.number} ❌ {e}")
            if _is_fatal_error(e):
                print()
                print("⛔ Arrêt : quota épuisé ou clé API invalide.")
                print(f"   ({ok}/{total} embeddings générés avant l'arrêt)")
                sys.exit(1)
            time.sleep(5)

    print(f"\n✅ {ok} embeddings générés.")


if __name__ == "__main__":
    main()
