"""
Charge les articles de la Constitution (et leurs embeddings) depuis la fixture
fournie, de maniere idempotente.

Pense pour le deploiement (Render, Docker, etc.) : la base de production demarre
vide. Cette commande la peuple en une seule etape, sans re-parser le PDF ni
regenerer les embeddings via une API payante.

Usage :
    python manage.py seed_constitution            # charge si la table est vide
    python manage.py seed_constitution --force     # recharge meme si non vide
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.constitution.models import ConstitutionArticle

FIXTURE = "constitution_articles"


class Command(BaseCommand):
    help = "Charge les articles de la Constitution depuis la fixture (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recharge la fixture meme si des articles existent deja.",
        )

    def handle(self, *args, **options):
        count = ConstitutionArticle.objects.count()

        if count and not options["force"]:
            self.stdout.write(
                self.style.WARNING(
                    f"{count} articles deja presents — seeding ignore. "
                    "Utilisez --force pour recharger."
                )
            )
            return

        self.stdout.write("Chargement de la fixture des articles constitutionnels…")
        call_command("loaddata", FIXTURE, verbosity=1)

        total = ConstitutionArticle.objects.count()
        with_embeddings = ConstitutionArticle.objects.exclude(embedding=None).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"OK — {total} articles charges ({with_embeddings} avec embedding)."
            )
        )
