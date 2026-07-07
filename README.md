# Module IA d’aide à la décision (Power BI e-learning)

Application locale qui permet:
- de choisir une page du rapport Power BI (Global, Genre, Tranche d’âge, Tranche d’ancienneté, Réseau Siège, En cours)
- d’uploader une capture (PNG/JPG) ou un export PDF de la page
- d’analyser le visuel via un modèle IA multimodal (OpenAI)
- de générer un rapport texte + un PDF professionnel téléchargeable

## Prérequis
- Python 3.10+
- Une clé API OpenAI

## Installation

Dans le dossier `app/`:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Copiez `.env.example` vers `.env` puis renseignez :
- `OPENAI_API_KEY` — clé API OpenAI du projet (format `sk-proj-...`)
- `OPENAI_PROJECT_ID` — identifiant du projet OpenAI (ex. `proj_...`)
- `OPENAI_ORGANIZATION_ID` — identifiant de l'organisation (ex. `org_...`)
- `MODEL_NAME` — ex. `gpt-4o` (modèle avec vision)
- `OPENAI_MAX_TOKENS` — optionnel (défaut : 3500)
- `OPENAI_TIMEOUT_SECONDS` — optionnel (ex. 120)

Ce module utilise **uniquement** l'API OpenAI (`https://api.openai.com/v1`).
`OPENAI_BASE_URL` et les fournisseurs tiers (OpenRouter, etc.) ne sont pas supportés.

## Lancer l’application

Depuis `app/`:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Ouvrir ensuite `http://127.0.0.1:8000`.

## Dossiers
- `uploads/`: fichiers importés
- `reports/`: PDFs générés

## Notes
- La clé API n’est jamais exposée côté frontend (elle reste dans `.env` côté backend).
- Si vous importez un PDF Power BI (6 pages), indiquez le **numéro de page** à analyser : seule cette page est convertie en image (1 = Global, 2 = Genre, 3 = Tranche d'age, 4 = Tranche d'ancienneté, 5 = Réseau Siège, 6 = En cours).

