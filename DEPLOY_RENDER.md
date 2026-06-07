# Déploiement sur Render

Ce projet est prêt pour un déploiement **Blueprint** sur [Render](https://render.com).
Le fichier `render.yaml` provisionne automatiquement :

- une base **PostgreSQL 16** (avec l'extension **pgvector** créée par la migration) ;
- un **Redis** (cache + broker Celery) ;
- le **service web Django** (gunicorn + WhiteNoise pour les fichiers statiques).

---

## 1. Prérequis

- Un compte Render.
- Ce dépôt poussé sur GitHub/GitLab.
- Une **clé API Gemini** gratuite : https://aistudio.google.com/app/apikey
  (et, en option, une clé OpenAI).

## 2. Déploiement en un clic (Blueprint)

1. Sur Render : **New +** → **Blueprint**.
2. Sélectionnez ce dépôt. Render détecte `render.yaml`.
3. Cliquez **Apply**. Render crée la base, le Redis et le service web.
4. Pendant le 1er build, `build.sh` exécute :
   - `pip install -r requirements.txt`
   - `collectstatic`
   - `migrate` (crée le schéma **et** l'extension pgvector)
   - `seed_constitution` (charge les **229 articles + embeddings** depuis la fixture)

## 3. Renseigner les secrets

Dans le dashboard du service **bcrdc-web** → **Environment**, complétez les
variables marquées « sync: false » :

| Variable | Valeur |
|----------|--------|
| `GEMINI_API_KEY` | votre clé Gemini (obligatoire pour l'IA) |
| `OPENAI_API_KEY` | optionnel (laisser vide si non utilisé) |
| `SITE_URL` | `https://<votre-app>.onrender.com` |

`SECRET_KEY` et `PHONE_HASH_PEPPER` sont générés automatiquement.
`DATABASE_URL`, `REDIS_URL`, `ALLOWED_HOSTS` et le CSRF sont gérés
automatiquement.

Après modification des variables, **Manual Deploy → Deploy latest commit**
(ou attendez le redéploiement automatique).

## 4. Créer un compte admin

Dans **bcrdc-web** → **Shell** :

```bash
python manage.py createsuperuser
```

Puis connectez-vous sur `https://<votre-app>.onrender.com/admin/`.

---

## Notes importantes

### Plan gratuit
- Le service web **gratuit** se met en veille après inactivité (premier accès
  plus lent). La base gratuite expire après 90 jours.
- Les **workers Celery ne sont pas gratuits** sur Render. L'application
  fonctionne sans : les tâches asynchrones (classification IA des arguments,
  rafraîchissement des statistiques) sont simplement ignorées proprement.
  Pour les activer, décommentez les services `worker` dans `render.yaml`
  (plan payant requis).

### Données de la Constitution
Les articles et leurs embeddings sont fournis dans la fixture
`apps/constitution/fixtures/constitution_articles.json` et chargés par
`seed_constitution` au déploiement. **Aucun re-parsing du PDF ni appel API
d'embedding n'est nécessaire en production.**

Pour régénérer la fixture après une mise à jour locale des articles :

```bash
# Windows PowerShell
$env:PYTHONUTF8=1
python manage.py dumpdata constitution.ConstitutionArticle --indent 2 `
  -o apps/constitution/fixtures/constitution_articles.json
```

### Santé
Sonde de disponibilité exposée sur `/healthz/` (utilisée par `healthCheckPath`).

### Recherche sémantique
Le modèle d'embedding (`gemini-embedding-001`, 768 dims) et le modèle de chat
(`gemini-2.5-flash`) sont définis via variables d'environnement et modifiables
sans toucher au code.
