import logging
from config.celery import app
from apps.constitution.models import ConstitutionArticle
from apps.consultation.models import Vote, ARGUMENT_CATEGORY

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3)
def generate_embeddings_task(self, article_ids: list[int] | None = None):
    """
    Generates OpenAI embeddings for ConstitutionArticle objects.
    If article_ids is None, processes all articles without embeddings.
    """
    from .rag import embed_text

    qs = ConstitutionArticle.objects.filter(embedding=None)
    if article_ids:
        qs = ConstitutionArticle.objects.filter(pk__in=article_ids)

    total = qs.count()
    logger.info(f"Generating embeddings for {total} articles.")

    for i, article in enumerate(qs, 1):
        try:
            text = f"Article {article.number}: {article.title}\n{article.content}"
            article.embedding = embed_text(text)
            article.save(update_fields=["embedding"])
            logger.info(f"[{i}/{total}] Article {article.number} embedded.")
        except Exception as exc:
            logger.error(f"Embedding failed for article {article.number}: {exc}")
            self.retry(exc=exc, countdown=60)


@app.task
def classify_vote_argument_task(vote_id: int):
    """Classifies a single vote's justification using the AI."""
    from .rag import classify_argument

    try:
        vote = Vote.objects.get(pk=vote_id)
        if vote.argument_category != ARGUMENT_CATEGORY.NON_CLASSE:
            return
        category = classify_argument(vote.justification)
        vote.argument_category = category
        vote.save(update_fields=["argument_category"])
        logger.info(f"Vote {vote_id} classified as: {category}")
    except Vote.DoesNotExist:
        logger.error(f"Vote {vote_id} not found.")


@app.task
def refresh_stats_snapshot_task():
    """Refreshes the VoteStatSnapshot. Run periodically via Celery beat."""
    from apps.consultation.services import get_or_refresh_snapshot
    snapshot = get_or_refresh_snapshot()
    logger.info(f"Stats snapshot refreshed: {snapshot.total_votes} total votes.")
