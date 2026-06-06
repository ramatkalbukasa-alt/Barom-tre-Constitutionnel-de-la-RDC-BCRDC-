from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .rag import ask_constitution
from .models import AIQuery


@require_http_methods(["GET"])
def ask_view(request):
    return render(request, "ai_engine/ask.html")


@require_http_methods(["POST"])
def ask_htmx(request):
    question = request.POST.get("question", "").strip()
    language = request.POST.get("language", "fr")

    if not question or len(question) < 5:
        return render(request, "ai_engine/partials/answer.html", {
            "error": "Veuillez poser une question d'au moins 5 caractères."
        })

    result = ask_constitution(question, language)

    query = AIQuery.objects.create(
        question=question,
        language=language,
        response_fr=result.get("fr", ""),
        response_lingala=result.get("lingala", ""),
        tokens_used=result.get("tokens_used", 0),
    )
    if result.get("articles_objects"):
        query.articles_used.set(result["articles_objects"])

    return render(request, "ai_engine/partials/answer.html", {
        "result": result,
        "question": question,
        "language": language,
    })
