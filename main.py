import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ai_analyzer import analyze_powerbi_page, get_default_page_prompt
from pdf_generator import generate_pdf_report, generate_strategic_pdf_report
from strategic_analyzer import analyze_strategic_report, extract_text_from_pdf
from utils import ensure_dirs, load_image_from_upload


load_dotenv(override=True)
os.environ.pop("OPENAI_BASE_URL", None)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
REPORT_DIR = BASE_DIR / "reports"

ensure_dirs([UPLOAD_DIR, REPORT_DIR])

app = FastAPI(title="Power BI e-learning IA - Aide à la décision")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

POWERBI_PAGE_OPTIONS = [
    {"number": 1, "name": "Global", "label": "1 - Global"},
    {"number": 2, "name": "Genre", "label": "2 - Genre"},
    {"number": 3, "name": "Tranche d'âge", "label": "3 - Tranche d'age"},
    {"number": 4, "name": "Tranche d'ancienneté", "label": "4 - Tranche d'ancienneté"},
    {"number": 5, "name": "Réseau Siège", "label": "5 - Réseau Siège"},
    {"number": 6, "name": "En cours", "label": "6 - En cours"},
]

POWERBI_PAGES = {p["number"]: p["name"] for p in POWERBI_PAGE_OPTIONS}


def _safe_slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "page"


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    page_prompts = {
        str(p["number"]): get_default_page_prompt(p["name"], p["number"])
        for p in POWERBI_PAGE_OPTIONS
    }
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "pages": POWERBI_PAGE_OPTIONS,
            "page_prompts": page_prompts,
            "page_prompts_json": json.dumps(page_prompts, ensure_ascii=False),
        },
    )


@app.get("/analyze")
async def analyze_get_redirect():
    return RedirectResponse(url="/", status_code=303)


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request,
    page_number: int = Form(...),
    prompt: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    if page_number not in POWERBI_PAGES:
        raise HTTPException(
            status_code=400,
            detail="Numéro de page invalide. Choisissez une page entre 1 et 6.",
        )

    page_name = POWERBI_PAGES[page_number]
    page_label = next(p["label"] for p in POWERBI_PAGE_OPTIONS if p["number"] == page_number)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Fichier manquant.")

    ext = Path(file.filename).suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".pdf"}:
        raise HTTPException(status_code=400, detail="Format non supporté (PNG/JPG/JPEG/PDF).")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_path = UPLOAD_DIR / f"upload_{ts}{ext}"

    try:
        contents = await file.read()
        upload_path.write_bytes(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'upload: {e}")

    try:
        image = load_image_from_upload(upload_path, pdf_page_number=page_number)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Impossible de lire le fichier: {e}")

    try:
        analysis_text = analyze_powerbi_page(
            page_name=page_name,
            page_number=page_number,
            image=image,
            user_prompt=prompt,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur IA: {e}")

    pdf_name = f"rapport_ia_p{page_number}_{_safe_slug(page_name)}_{datetime.now().strftime('%Y%m%d')}.pdf"
    pdf_path = REPORT_DIR / pdf_name

    try:
        generate_pdf_report(
            output_path=pdf_path,
            page_name=page_name,
            page_label=page_label,
            analysis_text=analysis_text,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération PDF: {e}")

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "page_label": page_label,
            "page_name": page_name,
            "analysis_text": analysis_text,
            "pdf_filename": pdf_name,
        },
    )


@app.get("/strategic", response_class=HTMLResponse)
def strategic(request: Request):
    existing_reports = sorted(
        [f.name for f in REPORT_DIR.iterdir() if f.suffix == ".pdf"],
        reverse=True,
    )
    return templates.TemplateResponse(
        request,
        "strategic.html",
        {"existing_reports": existing_reports},
    )


@app.post("/strategic-analyze", response_class=HTMLResponse)
async def strategic_analyze(
    request: Request,
    existing_report: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    pdf_to_analyze: Path
    source_name: str

    if file and file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext != ".pdf":
            raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés.")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        upload_path = UPLOAD_DIR / f"strategic_{ts}.pdf"
        try:
            contents = await file.read()
            upload_path.write_bytes(contents)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur d'upload: {e}")
        pdf_to_analyze = upload_path
        source_name = file.filename
    elif existing_report and existing_report.strip():
        if "/" in existing_report or "\\" in existing_report:
            raise HTTPException(status_code=400, detail="Nom de fichier invalide.")
        pdf_to_analyze = REPORT_DIR / existing_report.strip()
        if not pdf_to_analyze.exists():
            raise HTTPException(status_code=404, detail="Rapport introuvable.")
        source_name = existing_report.strip()
    else:
        raise HTTPException(status_code=400, detail="Sélectionne un rapport existant ou importe un PDF.")

    try:
        report_text = extract_text_from_pdf(pdf_to_analyze)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Impossible de lire le PDF: {e}")

    if not report_text.strip():
        raise HTTPException(status_code=400, detail="Le PDF ne contient pas de texte extractible.")

    try:
        analysis_text = analyze_strategic_report(report_text=report_text, source_name=source_name)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur IA: {e}")

    pdf_name = f"rapport_strategique_{_safe_slug(source_name)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = REPORT_DIR / pdf_name
    try:
        generate_strategic_pdf_report(
            output_path=pdf_path,
            source_name=source_name,
            analysis_text=analysis_text,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération PDF: {e}")

    return templates.TemplateResponse(
        request,
        "strategic_result.html",
        {
            "source_name": source_name,
            "analysis_text": analysis_text,
            "pdf_filename": pdf_name,
        },
    )


@app.get("/reports/{filename}")
def download_report(filename: str):
    # Sécurité: empêcher traversée de répertoires
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nom de fichier invalide.")

    path = REPORT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Rapport introuvable.")

    return FileResponse(
        str(path),
        media_type="application/pdf",
        filename=filename,
    )

