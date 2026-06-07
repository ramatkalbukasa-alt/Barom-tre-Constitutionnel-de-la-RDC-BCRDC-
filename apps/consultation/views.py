import json
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from apps.constitution.models import ConstitutionArticle
from .forms import VoteForm
from .models import Vote, VoteStatSnapshot, VOTE_CHOICE
from .services import compute_stats, get_or_refresh_snapshot, snapshot_to_stats

logger = logging.getLogger(__name__)


def _enqueue_argument_classification(vote_id: int) -> None:
    """Send the justification to the AI classifier in the background.
    Never let a broker/worker outage break the vote submission."""
    try:
        from apps.ai_engine.tasks import classify_vote_argument_task
        classify_vote_argument_task.delay(vote_id)
    except Exception as exc:  # pragma: no cover - depends on broker availability
        logger.warning("Could not enqueue argument classification for vote %s: %s", vote_id, exc)


def _get_session_user(request):
    from apps.users.models import CitizenUser
    user_id = request.session.get("verified_user_id")
    if not user_id:
        return None
    try:
        return CitizenUser.objects.get(pk=user_id, is_verified=True)
    except CitizenUser.DoesNotExist:
        return None


@require_http_methods(["GET", "POST"])
def vote(request):
    user = _get_session_user(request)
    if not user:
        messages.warning(request, "Vous devez d'abord vérifier votre numéro de téléphone.")
        return redirect("users:register")

    if user.has_voted:
        messages.info(request, "Vous avez déjà participé à la consultation. Merci !")
        return redirect("consultation:thank_you")

    if request.method == "POST":
        form = VoteForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            vote_obj = Vote.objects.create(
                user=user,
                choice=d["choice"],
                justification=d["justification"],
            )
            article_numbers = d.get("cited_article_numbers", [])
            if article_numbers:
                articles = ConstitutionArticle.objects.filter(number__in=article_numbers)
                vote_obj.cited_articles.set(articles)

            user.has_voted = True
            user.save(update_fields=["has_voted"])

            # Keep the cached stats fresh (cheap, no worker required) and send
            # the justification off for AI categorisation in the background.
            get_or_refresh_snapshot()
            _enqueue_argument_classification(vote_obj.pk)

            return redirect("consultation:thank_you")
    else:
        form = VoteForm()

    articles = ConstitutionArticle.objects.values("number", "title", "theme").order_by("number")
    return render(request, "consultation/vote.html", {
        "form": form,
        "articles": list(articles),
        "choices": VOTE_CHOICE.CHOICES,
        "choice_colors": VOTE_CHOICE.COLORS,
    })


def thank_you(request):
    user = _get_session_user(request)
    stats = compute_stats()
    return render(request, "consultation/thank_you.html", {"stats": stats, "user": user})


def _read_stats() -> dict:
    """Serve the cached snapshot; fall back to a live computation only when no
    snapshot exists yet (e.g. before the first vote)."""
    snapshot = VoteStatSnapshot.objects.filter(pk=1).first()
    if snapshot and snapshot.total_votes:
        return snapshot_to_stats(snapshot)
    return compute_stats()


def dashboard(request):
    stats = _read_stats()
    recent_votes = Vote.objects.select_related("user").order_by("-created_at")[:10]
    return render(request, "consultation/dashboard.html", {
        "stats": stats,
        "recent_votes": recent_votes,
        "stats_json": json.dumps(stats),
        "choice_colors": VOTE_CHOICE.COLORS,
    })


def dashboard_stats_htmx(request):
    return render(request, "consultation/partials/hero_stats.html", {"stats": _read_stats()})
