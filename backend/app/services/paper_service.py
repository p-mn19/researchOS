from datetime import datetime
from pathlib import Path
import re
import shutil
import uuid

from bson import ObjectId
from fastapi import HTTPException, UploadFile
from PyPDF2 import PdfReader

from app.config import settings
from app.db import papers_collection


STORAGE_DIR = Path(settings.storage_dir)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _safe_filename(filename: str) -> str:
    original_name = Path(filename).name
    stem = Path(original_name).stem
    suffix = Path(original_name).suffix.lower()
    safe_stem = re.sub(r"[^a-zA-Z0-9._-]", "_", stem)
    return f"{uuid.uuid4().hex}_{safe_stem}{suffix}"


def _extract_pdf_metadata(file_path: Path, fallback_filename: str):
    title = ""
    year = None
    authors = []

    try:
        reader = PdfReader(str(file_path))
        metadata = reader.metadata or {}

        raw_title = getattr(metadata, "title", None) or metadata.get("/Title")
        raw_author = getattr(metadata, "author", None) or metadata.get("/Author")

        if raw_title and str(raw_title).strip():
            title = str(raw_title).strip()

        if raw_author and str(raw_author).strip():
            authors = [a.strip() for a in str(raw_author).split(",") if a.strip()]

    except Exception:
        pass

    if not title:
        title = Path(fallback_filename).stem.replace("_", " ")

    return title, authors, year


def _validate_object_id(paper_id: str) -> ObjectId:
    paper_id = str(paper_id or "").strip()
    if not paper_id or not ObjectId.is_valid(paper_id):
        raise HTTPException(status_code=400, detail=f"Invalid paper ID: {paper_id!r}")
    return ObjectId(paper_id)


def _serialize_paper(document: dict) -> dict:
    return {
        "id": str(document["_id"]),
        "filename": document.get("filename", ""),
        "title": document.get("title", ""),
        "authors": document.get("authors", []),
        "year": document.get("year"),
        "abstract": document.get("abstract", ""),
        "uploaded_at": document.get("uploaded_at"),
        "status": document.get("status", "uploaded"),
        "methodology": document.get("methodology"),
        "dataset": document.get("dataset"),
        "limitations": document.get("limitations"),
    }


def create_paper_record(file: UploadFile):
    filename = file.filename or ""

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    stored_filename = _safe_filename(filename)
    save_path = STORAGE_DIR / stored_filename

    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not save uploaded file: {str(exc)}") from exc

    title, authors, year = _extract_pdf_metadata(save_path, filename)
    now = datetime.utcnow()

    paper_document = {
        "filename": filename,
        "stored_filename": stored_filename,
        "filepath": str(save_path),
        "title": title,
        "authors": authors,
        "year": year,
        "abstract": "",
        "keywords": [],
        "references": [],
        "status": "uploaded",
        "uploaded_at": now,
        "parsed_at": None,
        "indexed_at": None,
        "extracted_at": None,
    }

    result = papers_collection.insert_one(paper_document)

    return {
        "id": str(result.inserted_id),
        "filename": filename,
        "title": title,
        "status": "uploaded",
    }


def list_papers():
    documents = papers_collection.find().sort("uploaded_at", -1)
    return [_serialize_paper(document) for document in documents]


def get_all_papers():
    return list_papers()


def get_paper_by_id(paper_id: str):
    object_id = _validate_object_id(paper_id)
    paper = papers_collection.find_one({"_id": object_id})
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return _serialize_paper(paper)


def update_paper_status(paper_id: str, status: str):
    allowed_statuses = {"uploaded", "parsed", "indexed", "extracted"}

    if status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    object_id = _validate_object_id(paper_id)

    result = papers_collection.update_one(
        {"_id": object_id},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Paper not found")

    return get_paper_by_id(paper_id)