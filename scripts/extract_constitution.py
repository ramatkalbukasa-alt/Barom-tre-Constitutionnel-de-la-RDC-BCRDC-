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
import unicodedata
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


def reflow_text(text: str) -> str:
    """Recolle les retours à la ligne du PDF qui coupent une phrase en plein milieu.

    pdfplumber insère un \\n à chaque retour visuel de ligne. On fusionne ces
    coupures (où la ligne précédente ne se termine pas par une ponctuation forte)
    en une espace, tout en conservant les vraies fins de phrase comme sauts de
    ligne. Cela rend le texte propre à la lecture sans casser la structure.
    """
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)  # mots coupés par un tiret
    lines = [ln.strip() for ln in text.split("\n")]
    out: list[str] = []
    for line in lines:
        if not line:
            out.append("")
            continue
        if out and out[-1] and not re.search(r"[.!?:;»)]$", out[-1]):
            out[-1] = f"{out[-1]} {line}"
        else:
            out.append(line)
    result = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", result).strip()


def _norm(s: str) -> str:
    """Lowercase, strip accents, drop apostrophes, collapse whitespace."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower()
    s = re.sub(r"[\u2019'`]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


# Structural-heading → theme rules. Order matters: most specific first.
# The constitution is organised by TITRE / Chapitre / Section, which is a far
# more reliable signal than counting keywords across the body.
_RAW_HEADING_RULES = [
    ("revision constitutionnelle", THEME.REVISION),
    ("dispositions transitoires et finales", THEME.DISPOSITIONS_FINALES),
    ("traites et accords internationaux", THEME.SOUVERAINETE),
    ("commission electorale", THEME.AUTRE),
    ("conseil superieur de l'audiovisuel", THEME.AUTRE),
    ("institutions d'appui a la democratie", THEME.AUTRE),
    ("conseil economique et social", THEME.AUTRE),
    # "rapports entre exécutif et législatif" contains "pouvoir executif",
    # so it MUST be matched before the bare "pouvoir executif" rule.
    ("rapports entre le pouvoir executif et le pouvoir legislatif", THEME.POUVOIR_LEGISLATIF),
    ("pouvoir executif", THEME.POUVOIR_EXECUTIF),
    ("pouvoir legislatif", THEME.POUVOIR_LEGISLATIF),
    ("pouvoir judiciaire", THEME.POUVOIR_JUDICIAIRE),
    ("finances publiques", THEME.FINANCES_PUBLIQUES),
    ("police nationale et des forces armees", THEME.FORCE_ARMEE),
    ("forces armees", THEME.FORCE_ARMEE),
    ("administration publique", THEME.POUVOIR_EXECUTIF),
    ("institutions politiques provinciales", THEME.ORGANISATION_TERRITORIALE),
    ("repartition des competences", THEME.ORGANISATION_TERRITORIALE),
    ("autorite coutumiere", THEME.ORGANISATION_TERRITORIALE),
    ("des provinces", THEME.ORGANISATION_TERRITORIALE),
    ("de la nationalite", THEME.SOUVERAINETE),
    ("de l'etat et de la souverainete", THEME.SOUVERAINETE),
    ("de la souverainete", THEME.SOUVERAINETE),
    ("de l'etat", THEME.SOUVERAINETE),
    ("droits civils et politiques", THEME.DROITS_FONDAMENTAUX),
    ("droits economiques", THEME.DROITS_FONDAMENTAUX),
    ("droits collectifs", THEME.DROITS_FONDAMENTAUX),
    ("devoirs du citoyen", THEME.DROITS_FONDAMENTAUX),
    ("droits humains", THEME.DROITS_FONDAMENTAUX),
    ("dispositions generales", THEME.SOUVERAINETE),
]
HEADING_THEME_RULES = [(_norm(text), theme) for text, theme in _RAW_HEADING_RULES]

_HEADING_RE = re.compile(r"(?m)^\s*(?:TITRE|CHAPITRE|SECTION)\b[^\n]*", re.IGNORECASE)


def build_section_map(full_text: str) -> list:
    """Returns sorted [(char_index, theme), ...] for each structural heading."""
    out = []
    for m in _HEADING_RE.finditer(full_text):
        line = m.group(0)
        if "...." in line:  # skip the table of contents (dotted leaders)
            continue
        norm = _norm(line)
        for needle, theme in HEADING_THEME_RULES:
            if needle in norm:
                out.append((m.start(), theme))
                break
    out.sort(key=lambda x: x[0])
    return out


def theme_for_index(section_map: list, idx: int) -> str:
    """Theme of the last heading appearing before character position `idx`."""
    theme = THEME.AUTRE
    for pos, th in section_map:
        if pos <= idx:
            theme = th
        else:
            break
    return theme


def refine_theme(base_theme: str, content: str, title: str) -> str:
    """Sub-section override: the Constitutional Court sits inside the judiciary
    section but deserves its own theme."""
    nc = _norm(content + " " + title)
    if base_theme == THEME.POUVOIR_JUDICIAIRE and nc.count("constitutionnel") >= 2:
        return THEME.JUSTICE_CONSTITUTIONNELLE
    return base_theme


def _keyword_theme(content: str, title: str) -> str:
    """Fallback used only when an article precedes any structural heading."""
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
        r"(?:^|\n)\s*(?:Articles?|Art\.?)\s+(\d+(?:er|ère)?)\s*[.:-]?\s*(.*?)(?=\n\s*(?:Articles?|Art\.?)\s+\d+|\Z)",
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

        # Les articles de la Constitution RDC ne portent pas de titre : ils sont
        # uniquement numérotés. Tout le corps appartient au contenu — découper la
        # première ligne comme "titre" coupait la phrase en deux à l'affichage.
        title = ""
        content = reflow_text(match.group(2).strip())

        if content and number not in [a["number"] for a in articles]:
            articles.append({
                "number": number,
                "title": title[:255],
                "content": content,
                "_start": match.start(),
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


def load_articles_to_db(articles: list[dict], section_map: list, dry_run: bool = False):
    created = 0
    updated = 0
    for art in articles:
        theme = theme_for_index(section_map, art.get("_start", -1))
        if theme == THEME.AUTRE:
            theme = _keyword_theme(art["content"], art["title"])
        theme = refine_theme(theme, art["content"], art["title"])
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
    section_map = build_section_map(full_text)

    print(f"\n{len(articles)} articles détectés dans le PDF.")

    if args.dry_run:
        print("\n--- MODE DRY RUN (aucune écriture en DB) ---")
        load_articles_to_db(articles, section_map, dry_run=True)
        return

    print(f"Insertion dans la base de données…")
    created, updated = load_articles_to_db(articles, section_map)
    total = ConstitutionArticle.objects.count()
    print(f"\n✅ Terminé : {created} créés, {updated} mis à jour.")
    print(f"Total en base : {total} articles.")


if __name__ == "__main__":
    main()
