import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from apps.constitution.models import ConstitutionArticle
from .forms import VoteForm
from .models import Vote, VOTE_CHOICE
from .services import compute_stats, get_or_refresh_snapshot


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

            get_or_refresh_snapshot()

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


def dashboard(request):
    snapshot = get_or_refresh_snapshot()
    stats = compute_stats()
    recent_votes = Vote.objects.select_related("user").order_by("-created_at")[:10]
    return render(request, "consultation/dashboard.html", {
        "snapshot": snapshot,
        "stats": stats,
        "recent_votes": recent_votes,
        "stats_json": json.dumps(stats),
        "choice_colors": VOTE_CHOICE.COLORS,
    })


def dashboard_stats_htmx(request):
    stats = compute_stats()
    return render(request, "consultation/partials/hero_stats.html", {"stats": stats})
