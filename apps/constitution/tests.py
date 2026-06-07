from django.test import TestCase

from apps.constitution.models import ConstitutionArticle, THEME


class SearchTests(TestCase):
    def setUp(self):
        ConstitutionArticle.objects.create(
            number=1,
            title="Souveraineté",
            content="La République Démocratique du Congo est un État de droit souverain.",
            theme=THEME.SOUVERAINETE,
        )
        ConstitutionArticle.objects.create(
            number=220,
            title="Clause intangible",
            content="La forme républicaine de l'État ne peut faire l'objet d'aucune révision.",
            theme=THEME.REVISION,
        )

    def test_number_query_returns_exact_article(self):
        resp = self.client.get("/constitution/", {"q": "220"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "220")

    def test_fulltext_query_runs(self):
        resp = self.client.get("/constitution/recherche/", {"q": "souverain"})
        self.assertEqual(resp.status_code, 200)

    def test_theme_filter(self):
        resp = self.client.get("/constitution/", {"theme": THEME.REVISION})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "220")


class ThemeChoiceTests(TestCase):
    def test_revision_theme_exists(self):
        keys = {value for value, _ in THEME.CHOICES}
        self.assertIn(THEME.REVISION, keys)
