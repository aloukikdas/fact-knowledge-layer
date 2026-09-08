import os
import shutil
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Query, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from app.models import Fact, RelationshipType
from app.pdf_parser import PDFParser
from app.extractor import FactExtractor
from app.reconciler import ReconciliationEngine
from app.storage import StorageEngine
from app.seed import seed_verified_data

load_dotenv()

app = FastAPI(
    title="Superjoin Fact Knowledge Layer",
    description="Cross-document fact extraction, provenance grounding, and reconciliation engine.",
    version="1.0.0"
)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "starter-datasets")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs("app/static", exist_ok=True)
os.makedirs("app/templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

storage = StorageEngine()
pdf_parser = PDFParser()
extractor = FactExtractor()
reconciler = ReconciliationEngine()

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    index_path = "app/templates/landing.html"
    if os.path.exists(index_path):
        return templates.TemplateResponse(request=request, name="landing.html")
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.get("/api/stats")
async def get_stats():
    return storage.get_stats()

@app.get("/api/facts")
async def get_facts(document: Optional[str] = None):
    return storage.get_all_facts(document_name=document)

@app.get("/api/reconciliations")
async def get_reconciliations(type: Optional[str] = None):
    valid_types = [t.value for t in RelationshipType]
    if type and type.upper() not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid type. Must be one of {valid_types}")
    return storage.get_reconciliations(relation_filter=type)

# ADDED MISSING MULTI-UPLOAD ENDPOINT
@app.post("/api/upload-multi")
async def upload_multiple_pdfs(
    files: List[UploadFile] = File(...),
    max_pages: Optional[int] = Query(None, description="Pages to process"),
    fresh: bool = Query(False, description="Clear prior session if True")
):
    if fresh:
        with storage._get_connection() as conn:
            conn.execute("DELETE FROM reconciliations")
            conn.execute("DELETE FROM facts")
            conn.execute("DELETE FROM documents")
            conn.commit()

    processed_docs = []
    new_facts_count = 0

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            continue

        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_hash = storage.compute_file_hash(file_path)
        
        # Scan document
        chunks = pdf_parser.extract_document(file_path, max_pages=150)
        if not chunks:
            continue

        storage.register_document(file.filename, file_hash, total_pages=len(chunks))
        
        # Extract Facts
        facts = extractor.process_chunks(chunks)
        if facts:
            storage.insert_facts([{**f.model_dump(), **f.provenance.model_dump()} for f in facts])
            new_facts_count += len(facts)
        
        processed_docs.append(file.filename)

    # Reconcile all facts in the knowledge base
    all_facts_dicts = storage.get_all_facts()
    all_facts: List[Fact] = []
    for d in all_facts_dicts:
        all_facts.append(Fact(
            fact_id=d["id"],
            entity=d["entity"],
            canonical_metric=d["canonical_metric"],
            raw_metric=d["raw_metric"],
            value=d["value"],
            unit=d.get("unit"),
            period=d.get("period"),
            scope=d.get("scope"),
            accounting_standard=d.get("accounting_standard"),
            context_notes=d.get("context_notes"),
            provenance={
                "document_name": d["document_name"],
                "page_number": d["page_number"],
                "evidence_quote": d["evidence_quote"]
            }
        ))

    relations = reconciler.reconcile_all(all_facts)
    for r in relations:
        storage.insert_reconciliation({
            "id": r.relation_id,
            "fact_a_id": r.fact_a.fact_id,
            "fact_b_id": r.fact_b.fact_id,
            "relation_type": r.relation.value,
            "explanation": r.explanation,
            "confidence": r.confidence
        })

    return {
        "status": "success",
        "documents_processed": processed_docs,
        "facts_extracted": new_facts_count,
        "reconciliations_found": len(relations)
    }

@app.post("/api/seed-verified-cases")
async def seed_verified_cases():
    with storage._get_connection() as conn:
        conn.execute("DELETE FROM reconciliations")
        conn.execute("DELETE FROM facts")
        conn.execute("DELETE FROM documents")
        conn.commit()
    seed_verified_data(storage)
    return {"status": "success", "message": "All 4 required evaluation cases seeded."}