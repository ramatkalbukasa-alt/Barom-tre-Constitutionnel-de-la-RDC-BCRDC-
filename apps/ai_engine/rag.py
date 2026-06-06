"""
RAG (Retrieval-Augmented Generation) engine for constitutional Q&A.

Pipeline:
  1. Embed the user question with text-embedding-3-small
  2. Find the k most relevant articles via cosine similarity (stored as JSON)
  3. Build a grounded prompt with the retrieved articles
  4. Call gpt-4o-mini for a neutral, cited, bilingual (FR + Lingala) answer
"""
import json
import math
import logging
from typing import Optional
from django.conf import settings
from django.db.models import Q

logger = logging.getLogger(__name__)


def _get_openai_client():
    import openai
    return openai.OpenAI(api_key=settings.OPENAI_API_KEY)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x ** 2 for x in a))
    norm_b = math.sqrt(sum(x ** 2 for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def embed_text(text: str) -> list[float]:
    client = _get_openai_client()
    response = client.embeddings.create(
        model=settings.OPENAI_EMBED_MODEL,
        input=text[:8000],
    )
    return response.data[0].embedding


def retrieve_relevant_articles(question: str, top_k: int = 5) -> list:
    """
    Retrieves the top_k most relevant ConstitutionArticle objects.
    Falls back to keyword search if no embeddings are available.
    """
    from apps.constitution.models import ConstitutionArticle

    articles_with_embeddings = ConstitutionArticle.objects.exclude(embedding=None)

    if not articles_with_embeddings.exists():
        logger.warning("No embeddings found — falling back to keyword search.")
        return _keyword_fallback(question, top_k)

    try:
        question_embedding = embed_text(question)
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return _keyword_fallback(question, top_k)

    scored = []
    for article in articles_with_embeddings:
        if article.embedding:
            sim = cosine_similarity(question_embedding, article.embedding)
            scored.append((sim, article))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [article for _, article in scored[:top_k]]


def _keyword_fallback(question: str, top_k: int = 5) -> list:
    from apps.constitution.models import ConstitutionArticle
    words = [w for w in question.split() if len(w) > 3]
    if not words:
        return list(ConstitutionArticle.objects.all()[:top_k])
    q = Q()
    for word in words[:5]:
        q |= Q(content__icontains=word) | Q(title__icontains=word)
    return list(ConstitutionArticle.objects.filter(q)[:top_k])


SYSTEM_PROMPT = """Tu es un assistant juridique spécialisé dans la Constitution de la République Démocratique du Congo.

Règles absolues :
1. Tu ne prends JAMAIS position politiquement.
2. Chaque affirmation doit être ancrée dans un article constitutionnel cité explicitement.
3. Tu expliques les articles de manière simple, accessible à tout citoyen.
4. Tu donnes ta réponse en DEUX langues : français (FR) et lingala (LG).
5. Format de réponse obligatoire JSON :
{
  "fr": "Réponse en français...",
  "lingala": "Réponse en lingala...",
  "articles_cites": [1, 35, 220],
  "avertissement": "Cette explication est informative et ne constitue pas un avis juridique."
}
"""


def ask_constitution(question: str, language: str = "fr") -> dict:
    """
    Full RAG pipeline: retrieve → prompt → generate → return.
    Returns a dict with keys: fr, lingala, articles_cites, articles_objects, tokens_used, error
    """
    articles = retrieve_relevant_articles(question)

    if not articles:
        return {
            "fr": "Je n'ai pas trouvé d'articles pertinents pour répondre à cette question.",
            "lingala": "Nayoki te ndako ya maloba oyo ekoki kozalisa biso.",
            "articles_cites": [],
            "articles_objects": [],
            "tokens_used": 0,
            "error": None,
        }

    articles_context = "\n\n".join([
        f"--- Article {a.number} ({a.title}) ---\n{a.content}"
        for a in articles
    ])

    user_message = f"""Question du citoyen : {question}

Articles constitutionnels pertinents :
{articles_context}

Réponds en JSON selon le format indiqué dans tes instructions."""

    try:
        client = _get_openai_client()
        response = client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            max_tokens=1200,
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        data["articles_objects"] = articles
        data["tokens_used"] = response.usage.total_tokens
        data["error"] = None
        return data
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return {
            "fr": "Une erreur est survenue lors de la génération de la réponse. Veuillez réessayer.",
            "lingala": "Likambo moko esalemaki. Sala lisusu.",
            "articles_cites": [a.number for a in articles],
            "articles_objects": articles,
            "tokens_used": 0,
            "error": str(e),
        }


def classify_argument(justification: str) -> str:
    """
    Classifies a vote justification into one of the argument categories.
    Returns the category key string.
    """
    from apps.consultation.models import ARGUMENT_CATEGORY

    if not settings.OPENAI_API_KEY:
        return ARGUMENT_CATEGORY.NON_CLASSE

    prompt = f"""Classifie cet argument d'un citoyen congolais sur la Constitution dans UNE seule catégorie.

Catégories :
- juridique : argument basé sur des articles constitutionnels, le droit, la loi
- politique : argument basé sur des partis, des leaders, des intérêts politiques
- emotionnel : argument basé sur les sentiments, la peur, l'espoir, l'attachement
- socioeconomique : argument basé sur l'économie, le développement, les inégalités sociales

Argument : "{justification[:500]}"

Réponds UNIQUEMENT avec le mot-clé : juridique, politique, emotionnel, ou socioeconomique."""

    try:
        client = _get_openai_client()
        response = client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=10,
        )
        result = response.choices[0].message.content.strip().lower()
        valid = {ARGUMENT_CATEGORY.JURIDIQUE, ARGUMENT_CATEGORY.POLITIQUE,
                 ARGUMENT_CATEGORY.EMOTIONNEL, ARGUMENT_CATEGORY.SOCIOECONOMIQUE}
        return result if result in valid else ARGUMENT_CATEGORY.NON_CLASSE
    except Exception as e:
        logger.error(f"Argument classification error: {e}")
        return ARGUMENT_CATEGORY.NON_CLASSE
