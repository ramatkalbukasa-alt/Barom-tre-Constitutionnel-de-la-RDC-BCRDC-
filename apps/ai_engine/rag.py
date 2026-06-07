"""
RAG (Retrieval-Augmented Generation) engine for constitutional Q&A.

Pipeline:
  1. Embed the user question with text-embedding-3-small
  2. Find the k most relevant articles via cosine similarity (stored as JSON)
  3. Build a grounded prompt with the retrieved articles
  4. Generate a neutral, cited, bilingual (FR + Lingala) answer

Fournisseurs LLM : OpenAI (gpt-4o-mini) en primaire, avec repli automatique
sur Google Gemini (gemini-1.5-flash, palier gratuit) si OpenAI echoue ou n'est
pas configure.
"""
import json
import logging
import re
from django.conf import settings
from django.db.models import Q

logger = logging.getLogger(__name__)


def _get_openai_client():
    import openai
    return openai.OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=getattr(settings, "OPENAI_TIMEOUT", 20.0),
        max_retries=2,
    )


def _openai_available() -> bool:
    return bool(getattr(settings, "OPENAI_API_KEY", ""))


def _gemini_available() -> bool:
    return bool(getattr(settings, "GEMINI_API_KEY", ""))


def _gemini_chat(prompt: str, *, json_mode: bool, max_tokens: int, temperature: float) -> str:
    """Appel Gemini renvoyant le texte brut de la reponse.

    Les modeles Gemini 2.5 consomment une partie du budget `max_output_tokens`
    pour leur raisonnement interne ("thinking"). On accorde donc une marge
    genereuse afin que la reponse JSON ne soit pas tronquee.
    """
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max(max_tokens * 4, 4096),
    }
    if json_mode:
        generation_config["response_mime_type"] = "application/json"
    model = genai.GenerativeModel(
        settings.GEMINI_CHAT_MODEL,
        generation_config=generation_config,
    )
    response = model.generate_content(prompt)
    text = (response.text or "").strip()
    # Filet de securite : retirer un eventuel encadrement markdown ```json … ```
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    return text


def llm_chat(
    system_prompt: str,
    user_message: str,
    *,
    json_mode: bool = False,
    max_tokens: int = 1200,
    temperature: float = 0.2,
) -> tuple[str, str, int]:
    """Genere une reponse via OpenAI, avec repli sur Gemini.

    Retourne (texte_brut, fournisseur, tokens_utilises).
    Leve une exception seulement si tous les fournisseurs echouent.
    """
    last_error: Exception | None = None

    if _openai_available():
        try:
            client = _get_openai_client()
            kwargs = {
                "model": settings.OPENAI_CHAT_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**kwargs)
            tokens = response.usage.total_tokens if response.usage else 0
            return response.choices[0].message.content, "openai", tokens
        except Exception as e:
            last_error = e
            logger.warning("OpenAI indisponible (%s) — repli sur Gemini.", e)

    if _gemini_available():
        try:
            # Gemini n'a pas de role systeme distinct : on prefixe le prompt.
            prompt = f"{system_prompt}\n\n{user_message}"
            text = _gemini_chat(
                prompt, json_mode=json_mode, max_tokens=max_tokens, temperature=temperature
            )
            return text, "gemini", 0
        except Exception as e:
            last_error = e
            logger.error("Gemini a aussi echoue : %s", e)

    raise RuntimeError(
        f"Aucun fournisseur LLM disponible. Derniere erreur : {last_error}"
        if last_error else "Aucune cle API LLM configuree (OPENAI_API_KEY ou GEMINI_API_KEY)."
    )


def _gemini_embed(text: str, task_type: str = "retrieval_document") -> list[float]:
    """Embedding Gemini gemini-embedding-001 (palier gratuit), sortie 768 dims."""
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    result = genai.embed_content(
        model=settings.GEMINI_EMBED_MODEL,
        content=text[:8000],
        task_type=task_type,
        output_dimensionality=settings.EMBED_DIMENSIONS,
    )
    return result["embedding"]


def embed_text(text: str) -> list[float]:
    """Vecteur semantique d'un texte.

    Fournisseur par defaut : Gemini (gratuit, 768 dims). Les vecteurs stockes et
    les vecteurs de requete doivent provenir du MEME modele : on ne melange donc
    pas OpenAI (1536) et Gemini (768).
    """
    if _gemini_available():
        return _gemini_embed(text)

    # Repli OpenAI uniquement si Gemini n'est pas configure.
    client = _get_openai_client()
    response = client.embeddings.create(
        model=settings.OPENAI_EMBED_MODEL,
        input=text[:8000],
    )
    return response.data[0].embedding


def retrieve_relevant_articles(question: str, top_k: int = 5) -> list:
    """
    Retrieves the top_k most relevant ConstitutionArticle objects using a
    pgvector cosine-distance search (backed by the HNSW index in Postgres).
    Falls back to keyword search if no embeddings are available.
    """
    from pgvector.django import CosineDistance
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

    return list(
        articles_with_embeddings.order_by(
            CosineDistance("embedding", question_embedding)
        )[:top_k]
    )


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
        raw, provider, tokens = llm_chat(
            SYSTEM_PROMPT, user_message, json_mode=True, max_tokens=1200, temperature=0.2
        )
        data = json.loads(raw)
        data["articles_objects"] = articles
        data["tokens_used"] = tokens
        data["provider"] = provider
        data["error"] = None
        return data
    except Exception as e:
        logger.error(f"LLM error (OpenAI + Gemini): {e}")
        return {
            "fr": "Une erreur est survenue lors de la génération de la réponse. Veuillez réessayer.",
            "lingala": "Likambo moko esalemaki. Sala lisusu.",
            "articles_cites": [a.number for a in articles],
            "articles_objects": articles,
            "tokens_used": 0,
            "provider": None,
            "error": str(e),
        }


def classify_argument(justification: str) -> str:
    """
    Classifies a vote justification into one of the argument categories.
    Returns the category key string.
    """
    from apps.consultation.models import ARGUMENT_CATEGORY

    if not (_openai_available() or _gemini_available()):
        return ARGUMENT_CATEGORY.NON_CLASSE

    system = "Tu es un classificateur. Reponds par un seul mot-cle, sans ponctuation."
    prompt = f"""Classifie cet argument d'un citoyen congolais sur la Constitution dans UNE seule catégorie.

Catégories :
- juridique : argument basé sur des articles constitutionnels, le droit, la loi
- politique : argument basé sur des partis, des leaders, des intérêts politiques
- emotionnel : argument basé sur les sentiments, la peur, l'espoir, l'attachement
- socioeconomique : argument basé sur l'économie, le développement, les inégalités sociales

Argument : "{justification[:500]}"

Réponds UNIQUEMENT avec le mot-clé : juridique, politique, emotionnel, ou socioeconomique."""

    try:
        raw, _provider, _tokens = llm_chat(
            system, prompt, json_mode=False, max_tokens=10, temperature=0
        )
        result = raw.strip().lower()
        valid = {ARGUMENT_CATEGORY.JURIDIQUE, ARGUMENT_CATEGORY.POLITIQUE,
                 ARGUMENT_CATEGORY.EMOTIONNEL, ARGUMENT_CATEGORY.SOCIOECONOMIQUE}
        for v in valid:
            if v in result:
                return v
        return ARGUMENT_CATEGORY.NON_CLASSE
    except Exception as e:
        logger.error(f"Argument classification error: {e}")
        return ARGUMENT_CATEGORY.NON_CLASSE
