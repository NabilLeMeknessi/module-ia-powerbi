from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

OPENAI_OFFICIAL_BASE_URL = "https://api.openai.com/v1"


@dataclass(frozen=True)
class OpenAISettings:
    api_key: str
    model: str
    timeout_s: Optional[float]
    max_tokens: int
    project_id: Optional[str] = None
    organization_id: Optional[str] = None


def load_openai_settings() -> OpenAISettings:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("MODEL_NAME", "gpt-4o").strip()
    timeout_s_raw = os.getenv("OPENAI_TIMEOUT_SECONDS", "").strip()
    max_tokens_raw = os.getenv("OPENAI_MAX_TOKENS", "4000").strip()

    if os.getenv("OPENAI_BASE_URL", "").strip():
        raise RuntimeError(
            "OPENAI_BASE_URL n'est pas supporté : ce module utilise uniquement l'API OpenAI officielle "
            f"({OPENAI_OFFICIAL_BASE_URL}). Supprime OPENAI_BASE_URL de ton fichier .env."
        )

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY manquante (voir .env).")

    if model.startswith("openai/"):
        model = model.split("/", 1)[1]

    timeout_s: Optional[float] = None
    if timeout_s_raw:
        try:
            timeout_s = float(timeout_s_raw)
        except ValueError:
            raise RuntimeError("OPENAI_TIMEOUT_SECONDS invalide (doit être un nombre).")

    try:
        max_tokens = int(max_tokens_raw)
    except ValueError:
        raise RuntimeError("OPENAI_MAX_TOKENS invalide (doit être un entier).")

    return OpenAISettings(
        api_key=api_key,
        model=model,
        timeout_s=timeout_s,
        max_tokens=max_tokens,
        project_id=os.getenv("OPENAI_PROJECT_ID", "").strip() or None,
        organization_id=os.getenv("OPENAI_ORGANIZATION_ID", "").strip() or None,
    )


def create_openai_client(settings: OpenAISettings):
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise RuntimeError(f"Package openai non installé ou invalide: {e}")

    client_kwargs = {
        "api_key": settings.api_key,
        "base_url": OPENAI_OFFICIAL_BASE_URL,
        "timeout": settings.timeout_s,
    }
    if settings.organization_id:
        client_kwargs["organization"] = settings.organization_id
    if settings.project_id:
        client_kwargs["project"] = settings.project_id

    return OpenAI(**client_kwargs)


def map_openai_error(exc: Exception) -> RuntimeError:
    try:
        from openai import (  # type: ignore
            APIConnectionError,
            APIStatusError,
            APITimeoutError,
            AuthenticationError,
            RateLimitError,
        )
    except Exception:
        return RuntimeError(str(exc))

    if isinstance(exc, AuthenticationError):
        return RuntimeError(
            "Authentification OpenAI invalide. Vérifie OPENAI_API_KEY dans .env "
            f"(clé API OpenAI officielle requise). Détail: {exc}"
        )
    if isinstance(exc, RateLimitError):
        return RuntimeError(
            "Quota OpenAI dépassé ou rate limit atteint. "
            "Vérifie ton plan/crédits OpenAI puis réessaie. "
            f"Détail: {exc}"
        )
    if isinstance(exc, APIStatusError):
        if exc.status_code == 402:
            return RuntimeError(
                "Paiement ou crédits OpenAI insuffisants pour cette requête. "
                "Vérifie ton compte OpenAI ou réduis OPENAI_MAX_TOKENS dans .env. "
                f"Détail: {exc}"
            )
        return RuntimeError(f"Erreur API OpenAI ({exc.status_code}): {exc}")
    if isinstance(exc, APITimeoutError):
        return RuntimeError(
            "Timeout réseau vers l'API OpenAI. "
            "Vérifie ta connexion ou augmente OPENAI_TIMEOUT_SECONDS (ex: 120). "
            f"Détail: {exc}"
        )
    if isinstance(exc, APIConnectionError):
        return RuntimeError(
            "Impossible de se connecter à l'API OpenAI (connexion, proxy, VPN ou firewall). "
            f"Détail: {exc}"
        )
    return RuntimeError(str(exc))
