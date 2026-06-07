"""Vérifie quelle base PostgreSQL Django utilise et si pgvector est disponible.

Usage:
    python scripts/check_db.py
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

import psycopg2
from django.conf import settings

db = settings.DATABASES["default"]
print("Django ->", f"{db['USER']}@{db['HOST']}:{db['PORT']}/{db['NAME']}")

host = db["HOST"] or "127.0.0.1"
url = f"postgres://{db['USER']}:{db['PASSWORD']}@{host}:{db['PORT']}/{db['NAME']}"

try:
    with psycopg2.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_available_extensions WHERE name = 'vector')"
            )
            avail = cur.fetchone()[0]
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            installed = cur.fetchone()[0]
    print("Version :", version[:90])
    print("pgvector disponible :", avail)
    print("pgvector installé  :", installed)
    if "PostgreSQL 16" in version and not avail:
        print()
        print("⚠️  Vous êtes sur PostgreSQL 16 LOCAL (pgAdmin) SANS pgvector.")
        print("    Utilisez la base Docker sur le port 5434 :")
        print("    DATABASE_URL=postgres://bcrdc_user:bcrdc_pass@127.0.0.1:5434/bcrdc_db")
except Exception as exc:
    print("ERREUR de connexion :", exc)
