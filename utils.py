from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pypdfium2 as pdfium
from PIL import Image


def ensure_dirs(paths: Iterable[Path]) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def load_image_from_upload(path: Path, pdf_page_number: int = 1) -> Image.Image:
    ext = path.suffix.lower()
    if ext in {".png", ".jpg", ".jpeg"}:
        return Image.open(path).convert("RGB")

    if ext == ".pdf":
        if pdf_page_number < 1:
            raise ValueError("Le numéro de page doit être au moins 1.")
        pdf = pdfium.PdfDocument(str(path))
        if len(pdf) < 1:
            raise ValueError("PDF vide.")
        page_index = pdf_page_number - 1
        if page_index >= len(pdf):
            raise ValueError(
                f"Le PDF contient {len(pdf)} page(s). "
                f"La page {pdf_page_number} est introuvable."
            )
        page = pdf[page_index]
        # Qualité lisible pour dashboards (augmenter scale si besoin)
        pil_image = page.render(scale=2.0).to_pil()
        return pil_image.convert("RGB")

    raise ValueError("Format non supporté.")

