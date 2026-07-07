import base64
from io import BytesIO
from typing import Optional

from PIL import Image

from openai_config import create_openai_client, load_openai_settings, map_openai_error


_PROMPT_HEADER = """Tu es un analyste BI senior spécialisé en formation e-learning, RH et aide à la décision.
Tu analyses une page Power BI issue d'un tableau de bord de suivi des apprenants sur une plateforme e-learning Moodle.

Page analysée : {page_label} (page {page_number} du rapport Power BI — {page_name})
"""

_PROMPT_FOOTER = """
Le rapport doit contenir :
- Réécrire le texte de la formule de chaque KPI visible
- Résumé exécutif
- Analyse des KPI principaux
- Analyse des graphiques
- Points forts
- Points faibles
- Alertes
- Recommandations
- Conclusion décisionnelle

Important :
Ne pas inventer de chiffres qui ne sont pas visibles.
Si une donnée est illisible, le signaler clairement.
Le ton doit être professionnel, analytique et orienté décision."""

PAGE_PROMPTS: dict[str, str] = {
    "Global": """
Contexte : page de synthèse globale du dispositif e-learning GCAM.

Ta mission sur cette page :
1. Lire et interpréter les KPI globaux (taux de complétion, taux de réussite, score moyen, nombre d'inscriptions, nombre d'employés, taux d'absentéisme, taux d'abandon).
2. Identifier la santé globale du dispositif de formation (niveau de maturité, dynamique générale).
3. Repérer les écarts significatifs entre les indicateurs (ex. bonne complétion mais faible réussite).
4. Comparer les tendances temporelles si des graphiques d'évolution sont visibles.
5. Formuler des recommandations prioritaires pour la direction formation / DRH à l'échelle de l'organisation.
""",
    "Genre": """
Contexte : page d'analyse par genre (Masculin / Féminin).

Ta mission sur cette page :
1. Analyser les KPI par genre : taux de complétion, taux de réussite, score moyen, inscriptions, absentéisme.
2. Identifier les écarts de performance entre les deux genres (participation, complétion, réussite).
3. Détecter d'éventuelles disparités significatives nécessitant une action RH ou formation.
4. Commenter les graphiques comparatifs (barres, courbes, matrices) visibles sur la page.
5. Proposer des actions concrètes pour réduire les écarts ou renforcer l'engagement du segment le moins performant.
""",
    "Tranche d'âge": """
Contexte : page d'analyse par tranche d'âge (<30, [30-39], [40-49], [50-59], >59).

Ta mission sur cette page :
1. Analyser les KPI par tranche d'âge : complétion, réussite, score moyen, volume d'inscriptions.
2. Identifier quelle(s) tranche(s) d'âge sont les plus et les moins engagées.
3. Repérer des profils à risque (faible participation, fort absentéisme, faible score).
4. Interpréter les graphiques de répartition et de comparaison inter-tranches.
5. Recommander des actions ciblées par génération (modalités pédagogiques, relances, parcours adaptés).
""",
    "Tranche d'ancienneté": """
Contexte : page d'analyse par tranche d'ancienneté (<1 an, ]1-5], ]5-10], ]10-20], ]20-30], >30 ans).

Ta mission sur cette page :
1. Analyser les KPI par ancienneté : complétion, réussite, score moyen, inscriptions.
2. Identifier si les nouveaux arrivants ou les collaborateurs anciens performent différemment.
3. Détecter les segments d'ancienneté sous-performants ou désengagés.
4. Commenter les tendances visibles sur les graphiques par tranche d'ancienneté.
5. Proposer des actions RH/formation adaptées (onboarding, recyclage, montée en compétences).
""",
    "Réseau Siège": """
Contexte : page d'analyse par réseau (RS) et siège (SG).

Ta mission sur cette page :
1. Analyser les KPI par zone géographique / organisationnelle : complétion, réussite, score moyen, inscriptions, absentéisme.
2. Comparer les performances Réseau vs Siège et identifier la meilleure et la moins performante.
3. Repérer les écarts significatifs entre entités (top région, worst région si visible).
4. Interpréter les graphiques de comparaison inter-régions ou inter-entités.
5. Formuler des recommandations de pilotage différencié par réseau ou siège.
""",
    "En cours": """
Contexte : page de suivi des formations en cours (filtres par tranche d'âge et par formation).

Ta mission sur cette page :
1. Analyser l'état d'avancement des formations actuellement en cours.
2. Identifier les formations ou populations avec un faible taux de complétion ou un risque d'abandon.
3. Repérer les apprenants ou groupes en retard par rapport à l'objectif.
4. Commenter les indicateurs de progression, scores partiels et volumes en cours.
5. Proposer des actions opérationnelles immédiates (relances, accompagnement, ajustement des délais).
""",
}


def get_page_prompt(page_name: str) -> str:
    """Retourne le prompt fixe associé à une page Power BI."""
    return PAGE_PROMPTS.get(page_name, PAGE_PROMPTS["Global"])


def _format_prompt_vars(text: str, page_name: str, page_number: int, page_label: str) -> str:
    if any(p in text for p in ("{page_name}", "{page_number}", "{page_label}")):
        return text.format(
            page_name=page_name,
            page_number=page_number,
            page_label=page_label,
        )
    return text


def get_default_page_prompt(page_name: str, page_number: int) -> str:
    """Retourne le prompt fixe complet (en-tête + page + pied) pour affichage ou copie."""
    page_label = f"{page_number} - {page_name}"
    return (
        _PROMPT_HEADER.format(
            page_name=page_name,
            page_number=page_number,
            page_label=page_label,
        )
        + get_page_prompt(page_name)
        + _PROMPT_FOOTER
    )


def build_analysis_prompt(
    page_name: str,
    page_number: int,
    user_prompt: Optional[str] = None,
) -> str:
    page_label = f"{page_number} - {page_name}"
    default_prompt = get_default_page_prompt(page_name, page_number)

    custom = (user_prompt or "").strip()
    if custom:
        return _format_prompt_vars(custom, page_name, page_number, page_label)

    return default_prompt


def _image_to_data_url(image: Image.Image) -> str:
    buf = BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def analyze_powerbi_page(
    page_name: str,
    page_number: int,
    image: Image.Image,
    user_prompt: Optional[str] = None,
) -> str:
    settings = load_openai_settings()
    client = create_openai_client(settings)
    prompt = build_analysis_prompt(
        page_name=page_name,
        page_number=page_number,
        user_prompt=user_prompt,
    )
    data_url = _image_to_data_url(image)

    try:
        resp = client.chat.completions.create(
            model=settings.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            max_tokens=settings.max_tokens,
        )
    except Exception as e:
        raise map_openai_error(e)

    content = resp.choices[0].message.content
    if not content:
        raise RuntimeError("Réponse IA vide.")
    return content.strip()
