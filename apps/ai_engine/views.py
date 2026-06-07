from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit
from .rag import ask_constitution
from .models import AIQuery


FAQ_QUESTIONS = [
    "Que dit la Constitution sur le mandat présidentiel ?",
    "Quels sont les droits fondamentaux garantis par la Constitution ?",
    "Comment peut-on réviser la Constitution ?",
    "Quelles sont les attributions du Président de la République ?",
    "Quels sont les pouvoirs du Parlement ?",
    "Comment fonctionne la Cour Constitutionnelle ?",
]


@require_http_methods(["GET"])
def ask_view(request):
    return render(request, "ai_engine/ask.html", {"faq_questions": FAQ_QUESTIONS})


@ratelimit(key="ip", rate="15/h", method="POST", block=False)
@ratelimit(key="ip", rate="3/m", method="POST", block=False)
@require_http_methods(["POST"])
def ask_htmx(request):  # CSRF handled via {% csrf_token %} in form body
    if getattr(request, "limited", False):
        return render(request, "ai_engine/partials/answer.html", {
            "error": "Vous avez atteint la limite de questions. Veuillez réessayer plus tard."
        })

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
