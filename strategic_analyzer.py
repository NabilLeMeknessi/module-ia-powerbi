from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium

from openai_config import create_openai_client, load_openai_settings, map_openai_error


STRATEGIC_PROMPT = """Tu es un consultant senior en stratégie RH et formation, expert en analyse de performance e-learning.

Tu reçois un rapport d'analyse BI sur un tableau de bord de suivi des apprenants sur une plateforme Moodle.
Source du rapport : {source_name}

--- RAPPORT BI ANALYSÉ ---
{report_text}
--- FIN DU RAPPORT ---

Ta mission : extraire les insights clés et formuler des recommandations décisionnelles précises destinées à la direction (DRH / CODIR).
Ne pas répéter le contenu du rapport — synthétiser et orienter vers l'action.

Ton rapport doit contenir les sections suivantes :

1. SYNTHÈSE EXÉCUTIVE
   Résumé en 5 lignes maximum des principaux enseignements du rapport.

2. ÉTAT DE SANTÉ DES KPIs
   Pour chaque KPI identifié, préciser : Nom | Valeur | État (Bon / À surveiller / Critique) | Commentaire court.

3. POINTS CRITIQUES — ACTION IMMÉDIATE REQUISE
   Les 3 problèmes les plus urgents qui nécessitent une décision rapide de la direction.

4. RECOMMANDATIONS DÉCISIONNELLES (priorisées)
   Pour chaque recommandation :
   - Action concrète à entreprendre
   - Responsable suggéré (ex : DRH, Responsable Formation, Management)
   - Impact attendu (quantifié si possible)

5. RISQUES EN CAS D'INACTION
   Conséquences potentielles si aucune mesure n'est prise à court terme.

6. PLAN D'ACTION SUGGÉRÉ
   - Court terme (< 1 mois) : actions immédiates
   - Moyen terme (1–3 mois) : mesures structurelles
   - Long terme (> 3 mois) : transformations stratégiques

Le ton doit être directif, orienté décision, adapté à un comité de direction ou DRH."""


def extract_text_from_pdf(path: Path) -> str:
    pdf = pdfium.PdfDocument(str(path))
    parts: list[str] = []
    for i in range(len(pdf)):
        page = pdf[i]
        textpage = page.get_textpage()
        parts.append(textpage.get_text_range())
    return "\n".join(parts)


def analyze_strategic_report(report_text: str, source_name: str) -> str:
    settings = load_openai_settings()
    client = create_openai_client(settings)
    prompt = STRATEGIC_PROMPT.format(source_name=source_name, report_text=report_text)

    try:
        resp = client.chat.completions.create(
            model=settings.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=settings.max_tokens,
        )
    except Exception as e:
        raise map_openai_error(e)

    content = resp.choices[0].message.content
    if not content:
        raise RuntimeError("Réponse IA vide.")
    return content.strip()
