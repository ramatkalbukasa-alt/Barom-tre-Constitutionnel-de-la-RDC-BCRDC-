"""
Script d'extraction de la Constitution RDC depuis le PDF.

Usage:
    python scripts/extract_constitution.py

Ce script :
1. Lit le PDF JOS.05.02.2011.pdf avec pdfplumber
2. Extrait chaque article (numéro, titre, contenu)
3. Détermine le thème automatiquement via des mots-clés
4. Insère les articles dans la base de données PostgreSQL

À exécuter APRÈS avoir lancé les migrations Django.
"""
import os
import sys
import re
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

import pdfplumber
from pathlib import Path
from apps.constitution.models import ConstitutionArticle, THEME

PDF_PATH = Path(__file__).resolve().parent.parent / "JOS.05.02.2011.pdf"

THEME_KEYWORDS = {
    THEME.SOUVERAINETE: [
        "souveraineté", "état", "territoire", "peuple", "nation", "drapeau",
        "emblème", "hymne", "capitale", "langues officielles",
    ],
    THEME.DROITS_FONDAMENTAUX: [
        "droit", "liberté", "dignité", "égalité", "citoyen", "personne",
        "torture", "esclavage", "expression", "religion", "propriété",
        "éducation", "santé", "travail", "vote", "élu",
    ],
    THEME.POUVOIR_EXECUTIF: [
        "président", "gouvernement", "premier ministre", "ministre",
        "exécutif", "mandat présidentiel", "cabinet", "conseil des ministres",
    ],
    THEME.POUVOIR_LEGISLATIF: [
        "parlement", "assemblée nationale", "sénat", "sénateur", "député",
        "législatif", "loi", "promulgation", "session",
    ],
    THEME.POUVOIR_JUDICIAIRE: [
        "cour", "tribunal", "juge", "judiciaire", "magistrat",
        "cour suprême", "parquet", "procureur",
    ],
    THEME.ORGANISATION_TERRITORIALE: [
        "province", "décentralisation", "territoire", "ville",
        "commune", "secteur", "gouverneur", "assemblée provinciale",
    ],
    THEME.JUSTICE_CONSTITUTIONNELLE: [
        "cour constitutionnelle", "constitution", "inconstitutionnel",
        "référendum", "contrôle", "constitutionnalité",
    ],
    THEME.FINANCES_PUBLIQUES: [
        "budget", "impôt", "taxe", "finances", "trésor", "loi de finances",
        "ressources naturelles", "dette",
    ],
    THEME.FORCE_ARMEE: [
        "armée", "forces armées", "police", "sécurité", "défense",
        "service militaire", "forces de l'ordre",
    ],
    THEME.REVISION: [
        "révision", "modifier", "modification", "amendement", "intangible",
        "changement de constitution",
    ],
    THEME.DISPOSITIONS_FINALES: [
        "transitoire", "disposition finale", "abroge", "entre en vigueur",
        "présente constitution",
    ],
}


def detect_theme(content: str, title: str) -> str:
    text = (content + " " + title).lower()
    scores = {theme: 0 for theme in THEME_KEYWORDS}
    for theme, keywords in THEME_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[theme] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else THEME.AUTRE


def extract_keywords(content: str, max_kw: int = 8) -> list:
    stop_words = {
        "le", "la", "les", "de", "du", "des", "et", "en", "un", "une",
        "est", "sont", "par", "pour", "sur", "dans", "que", "qui", "il",
        "elle", "ils", "elles", "ou", "au", "aux", "se", "ce", "cet",
        "cette", "ces", "à", "d", "l", "s", "n", "y",
    }
    words = re.findall(r"\b[a-zàâçéèêëîïôûùüÿæœ]{4,}\b", content.lower())
    freq: dict[str, int] = {}
    for w in words:
        if w not in stop_words:
            freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq, key=freq.get, reverse=True)
    return sorted_words[:max_kw]


def parse_articles_from_text(full_text: str) -> list[dict]:
    """
    Parses the full extracted PDF text into individual articles.
    Handles patterns like:
      "Article 1er", "Article 1", "ARTICLE 1", "Art. 1"
    """
    pattern = re.compile(
        r"(?:^|\n)\s*(?:Article|ARTICLE|Art\.?)\s+(\d+(?:er|ère)?)\s*[.:-]?\s*(.*?)(?=\n\s*(?:Article|ARTICLE|Art\.?)\s+\d+|\Z)",
        re.DOTALL | re.IGNORECASE,
    )

    articles = []
    for match in pattern.finditer(full_text):
        raw_number = match.group(1).strip()
        number_str = re.sub(r"(er|ère)$", "", raw_number, flags=re.IGNORECASE)
        try:
            number = int(number_str)
        except ValueError:
            continue

        raw_body = match.group(2).strip()
        lines = raw_body.split("\n")
        title_line = lines[0].strip() if lines else ""
        remaining = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

        if len(title_line) < 100 and not title_line.endswith("."):
            title = title_line
            content = remaining or title_line
        else:
            title = ""
            content = raw_body

        content = re.sub(r"\n{3,}", "\n\n", content).strip()

        if content and number not in [a["number"] for a in articles]:
            articles.append({
                "number": number,
                "title": title[:255],
                "content": content,
            })

    articles.sort(key=lambda x: x["number"])
    return articles


def extract_text_from_pdf(pdf_path: Path) -> str:
    print(f"Lecture du PDF: {pdf_path}")
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text(x_tolerance=3, y_tolerance=3)
            if text:
                full_text += text + "\n"
            if i % 20 == 0:
                print(f"  Page {i}/{total}…")
    print(f"Extraction terminée. {len(full_text):,} caractères extraits.")
    return full_text


def load_articles_to_db(articles: list[dict], dry_run: bool = False) -> int:
    created = 0
    updated = 0
    for art in articles:
        theme = detect_theme(art["content"], art["title"])
        keywords = extract_keywords(art["content"])

        if dry_run:
            print(f"  Art.{art['number']:3d} | {theme:25s} | {art['title'][:50]}")
            continue

        obj, was_created = ConstitutionArticle.objects.update_or_create(
            number=art["number"],
            defaults={
                "title": art["title"],
                "content": art["content"],
                "theme": theme,
                "keywords": keywords,
                "language": "fr",
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return created, updated


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extrait la Constitution RDC du PDF vers la DB.")
    parser.add_argument("--dry-run", action="store_true", help="Affiche les articles sans les enregistrer.")
    parser.add_argument("--pdf", default=str(PDF_PATH), help="Chemin vers le PDF.")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"ERREUR: PDF introuvable à {pdf_path}")
        sys.exit(1)

    full_text = extract_text_from_pdf(pdf_path)
    articles = parse_articles_from_text(full_text)

    print(f"\n{len(articles)} articles détectés dans le PDF.")

    if args.dry_run:
        print("\n--- MODE DRY RUN (aucune écriture en DB) ---")
        load_articles_to_db(articles, dry_run=True)
        return

    print(f"Insertion dans la base de données…")
    created, updated = load_articles_to_db(articles)
    total = ConstitutionArticle.objects.count()
    print(f"\n✅ Terminé : {created} créés, {updated} mis à jour.")
    print(f"Total en base : {total} articles.")


if __name__ == "__main__":
    main()
