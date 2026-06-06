from django.shortcuts import render, get_object_or_404
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Q
from .models import ConstitutionArticle, THEME


def article_list(request):
    theme = request.GET.get("theme", "")
    query = request.GET.get("q", "").strip()
    articles = ConstitutionArticle.objects.all()

    if theme:
        articles = articles.filter(theme=theme)

    if query:
        articles = articles.filter(
            Q(title__icontains=query)
            | Q(content__icontains=query)
            | Q(number__icontains=query)
        )

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

    if query:
        articles = articles.filter(
            Q(title__icontains=query)
            | Q(content__icontains=query)
        )

    return render(request, "constitution/partials/article_results.html", {
        "articles": articles[:30],
        "query": query,
    })
