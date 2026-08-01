from fastapi import UploadFile, HTTPException
from bson import ObjectId
from datetime import datetime
from pathlib import Path
import shutil

from app.config import STORAGE_DIR
from app.db import papers_collection

def create_paper_record(file: UploadFile):
    filename = file.filename
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    save_path = STORAGE_DIR / filename
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    paper_doc = {
        "filename": filename,
        "filepath": str(save_path),
        "title": "",
        "authors": [],
        "year": None,
        "abstract": "",
        "keywords": [],
        "references": [],
        "status": "uploaded",
        "uploaded_at": datetime.utcnow(),
        "parsed_at": None,
        "indexed_at": None,
        "extracted_at": None,
    }

    result = papers_collection.insert_one(paper_doc)
    return {
        "id": str(result.inserted_id),
        "filename": filename,
        "title": "",
        "status": "uploaded",
    }

def list_papers():
    papers = []
    for p in papers_collection.find().sort("uploaded_at", -1):
        papers.append({
            "id": str(p["_id"]),
            "filename": p.get("filename", ""),
            "title": p.get("title", ""),
            "status": p.get("status", "uploaded"),
        })
    return papers

def get_paper_by_id(paper_id: str):
    paper = papers_collection.find_one({"_id": ObjectId(paper_id)})
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    paper["id"] = str(paper["_id"])
    del paper["_id"]
    return paper