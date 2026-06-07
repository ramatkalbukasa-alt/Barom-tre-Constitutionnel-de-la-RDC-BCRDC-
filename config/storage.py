"""Stockage des fichiers statiques pour la production.

WhiteNoise + ManifestStaticFilesStorage reecrit les references `url(...)` dans
les CSS et hash les noms de fichiers (cache-busting). Or des paquets tiers
comme django-jazzmin embarquent des CSS qui pointent vers des `*.css.map`
absents, ce qui fait echouer `collectstatic` avec une `MissingFileError`.

On etend le stockage pour ignorer proprement ces references manquantes tout en
conservant le hachage et la compression des fichiers reellement presents.
"""
from whitenoise.storage import CompressedManifestStaticFilesStorage


class WhiteNoiseStaticFilesStorage(CompressedManifestStaticFilesStorage):
    # Ne pas lever d'erreur au runtime si un fichier n'est pas dans le manifeste.
    manifest_strict = False

    def url_converter(self, name, hashed_files, template=None):
        converter = super().url_converter(name, hashed_files, template)

        def wrapped(matchobj):
            try:
                return converter(matchobj)
            except ValueError:
                # Reference (souvent un .map) introuvable : on laisse l'URL
                # d'origine telle quelle au lieu d'echouer.
                return matchobj.group(0)

        return wrapped
