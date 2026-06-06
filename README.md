# Baromètre Constitutionnel de la RDC (BCRDC)

Plateforme web de consultation citoyenne + moteur IA d'explication de la Constitution congolaise.

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Django 4.2 + DRF |
| Frontend | Django Templates + Tailwind CSS + Alpine.js + HTMX |
| Base de données | PostgreSQL 15 + pgvector |
| IA | OpenAI (gpt-4o-mini + text-embedding-3-small) |
| Queue | Celery + Redis |
| Admin | Django Admin + Jazzmin |

---

## Prérequis

- Python 3.11+
- PostgreSQL 15+
- Redis (pour Celery et le cache)
- Un compte OpenAI (pour la Phase 3 — IA)

---

## Installation

### 1. Environnement virtuel

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate    # Linux/macOS
```

### 2. Dépendances

```bash
pip install -r requirements.txt
```

### 3. Variables d'environnement

```bash
copy .env.example .env       # Windows
# cp .env.example .env        # Linux/macOS
```

Éditez `.env` et remplissez au minimum :
- `SECRET_KEY` : générez avec `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- `DATABASE_URL` : ex. `postgres://bcrdc_user:password@localhost:5432/bcrdc_db`
- `OPENAI_API_KEY` : votre clé OpenAI (Phase 3)

### 4. Base de données PostgreSQL

```sql
-- Dans psql :
CREATE DATABASE bcrdc_db;
CREATE USER bcrdc_user WITH PASSWORD 'bcrdc_pass';
GRANT ALL PRIVILEGES ON DATABASE bcrdc_db TO bcrdc_user;
```

### 5. Migrations Django

```bash
python manage.py migrate
```

### 6. Créer un superutilisateur (admin)

```bash
python manage.py createsuperuser
```
> Entrez uniquement un `phone_hash` (n'importe quelle chaîne) et un mot de passe.

### 7. Extraire la Constitution depuis le PDF

```bash
python scripts/extract_constitution.py --dry-run   # Vérification
python scripts/extract_constitution.py             # Import réel
```

### 8. Lancer le serveur de développement

```bash
python manage.py runserver
```

Ouvrez [http://localhost:8000](http://localhost:8000)

---

## Phase 3 — Génération des embeddings IA

Une fois `OPENAI_API_KEY` configurée et les articles en base :

```bash
python scripts/generate_embeddings.py
```

---

## Structure du projet

```
bcrdc/
├── config/               # Django settings (base, dev, prod)
├── apps/
│   ├── users/            # Auth + OTP + profil citoyen
│   ├── constitution/     # Articles + recherche
│   ├── consultation/     # Vote + statistiques + dashboard
│   └── ai_engine/        # RAG + classification arguments
├── templates/            # Django HTML templates
├── static/               # CSS, JS, images
├── scripts/              # PDF extraction + embedding generation
├── manage.py
└── requirements.txt
```

---

## Pages principales

| URL | Description |
|-----|-------------|
| `/` | Page d'accueil |
| `/constitution/` | Explorer les articles |
| `/constitution/article/<n>/` | Détail d'un article |
| `/ia/` | Assistant IA constitutionnel |
| `/participer/` | Inscription + OTP + vote |
| `/consultation/tableau-de-bord/` | Dashboard public |
| `/admin/` | Interface d'administration |

---

## Roadmap

- **Phase 1 (MVP)** ✅ — PDF extraction, constitution explorer, vote simple
- **Phase 2** — OTP hardening, dashboard stats en temps réel
- **Phase 3** — IA constitutionnelle, embeddings, multilingue (FR + Lingala)

---

## Neutralité et éthique

Cette plateforme est politiquement neutre. L'IA ne prend jamais position. Toute réponse est ancrée dans le texte constitutionnel officiel.
