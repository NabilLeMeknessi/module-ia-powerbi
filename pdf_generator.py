from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

LOGO_PATH = Path(__file__).parent / "static" / "logo.png"
LOGO_WIDTH = 3.2 * cm
LOGO_HEIGHT = 1.6 * cm


def _safe_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def _get_logo_image() -> Image | None:
    if not LOGO_PATH.exists():
        return None

    img = PILImage.open(LOGO_PATH).convert("RGBA")
    pixels = img.getdata()
    cleaned = []
    for r, g, b, a in pixels:
        if r < 35 and g < 35 and b < 35:
            cleaned.append((255, 255, 255, 0))
        else:
            cleaned.append((r, g, b, a))
    img.putdata(cleaned)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    logo = Image(buffer, width=LOGO_WIDTH, height=LOGO_HEIGHT, kind="proportional")
    logo.hAlign = "LEFT"
    return logo


def _append_report_header(
    story: list,
    title: str,
    title_style: ParagraphStyle,
    meta_html: str,
    meta_style: ParagraphStyle,
) -> None:
    logo = _get_logo_image()
    if logo:
        story.append(logo)
        story.append(Spacer(1, 10))

    centered_title_style = ParagraphStyle(
        f"{title_style.name}Centered",
        parent=title_style,
        alignment=TA_CENTER,
    )
    story.append(Paragraph(title, centered_title_style))
    story.append(Paragraph(meta_html, meta_style))
    story.append(Spacer(1, 8))


def generate_pdf_report(
    output_path: Path,
    page_name: str,
    analysis_text: str,
    page_label: str | None = None,
) -> None:
    display_page = page_label or page_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=f"Rapport IA - {display_page}",
        author="Module IA Power BI",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0B3D2E"),
        spaceAfter=12,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=10,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        spaceAfter=8,
    )

    story = []
    _append_report_header(
        story,
        title="Rapport IA d’aide à la décision",
        title_style=title_style,
        meta_html=(
            f"<b>Page analysée :</b> {display_page}<br/>"
            f"<b>Date :</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ),
        meta_style=meta_style,
    )

    story.append(Paragraph(_safe_html(analysis_text), body_style))
    doc.build(story)


def generate_strategic_pdf_report(output_path: Path, source_name: str, analysis_text: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="Rapport Stratégique IA - Aide à la Décision",
        author="Module IA Power BI",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "StrategicTitle",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A3A5C"),
        spaceAfter=12,
    )
    meta_style = ParagraphStyle(
        "StrategicMeta",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=10,
    )
    body_style = ParagraphStyle(
        "StrategicBody",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        spaceAfter=8,
    )

    story = []
    _append_report_header(
        story,
        title="Rapport Stratégique — Aide à la Décision",
        title_style=title_style,
        meta_html=(
            f"<b>Source :</b> {source_name}<br/>"
            f"<b>Date :</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ),
        meta_style=meta_style,
    )
    story.append(Paragraph(_safe_html(analysis_text), body_style))
    doc.build(story)

