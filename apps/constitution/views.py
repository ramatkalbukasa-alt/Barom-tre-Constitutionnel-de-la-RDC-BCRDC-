from django.shortcuts import render, get_object_or_404
from django.contrib.postgres.search import SearchQuery, SearchRank
from .models import ConstitutionArticle, THEME


def _apply_search(qs, query: str):
    """PostgreSQL full-text search (French config), ranked by relevance.
    Uses the GIN-indexed `search_vector` column. Pure-digit queries match an
    article number directly."""
    if not query:
        return qs
    if query.isdigit():
        return qs.filter(number=int(query))
    search = SearchQuery(query, config="french")
    return (
        qs.filter(search_vector=search)
        .annotate(rank=SearchRank("search_vector", search))
        .order_by("-rank")
    )


def article_list(request):
    theme = request.GET.get("theme", "")
    query = request.GET.get("q", "").strip()
    articles = ConstitutionArticle.objects.all()

    if theme:
        articles = articles.filter(theme=theme)

    articles = _apply_search(articles, query)

    themes = THEME.CHOICES
    context = {
        "articles": articles[:50],
        "themes": themes,
        "selected_theme": theme,
        "query": query,
        "total_count": ConstitutionArticle.objects.count(),
        "theme_icons": THEME.ICONS,
    }
    return render(request, "constitution/list.html", context)


def article_detail(request, number):
    article = get_object_or_404(ConstitutionArticle, number=number)
    prev_article = ConstitutionArticle.objects.filter(number__lt=number).order_by("-number").first()
    next_article = ConstitutionArticle.objects.filter(number__gt=number).order_by("number").first()

    context = {
        "article": article,
        "prev_article": prev_article,
        "next_article": next_article,
    }
    return render(request, "constitution/detail.html", context)


def article_search_htmx(request):
    query = request.GET.get("q", "").strip()
    theme = request.GET.get("theme", "")
    articles = ConstitutionArticle.objects.all()

    if theme:
        articles = articles.filter(theme=theme)

    articles = _apply_search(articles, query)

    return render(request, "constitution/partials/article_results.html", {
        "articles": articles[:30],
        "query": query,
    })
