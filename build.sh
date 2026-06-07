#!/usr/bin/env bash
# Build script execute par Render a chaque deploiement.
# https://render.com/docs/deploy-django
set -o errexit

pip install -r requirements.txt

# Fichiers statiques (servis par WhiteNoise).
python manage.py collectstatic --no-input

# Schema de base de donnees (cree aussi l'extension pgvector via la migration 0003).
python manage.py migrate

# Peuple la Constitution + embeddings depuis la fixture, uniquement si vide.
python manage.py seed_constitution
