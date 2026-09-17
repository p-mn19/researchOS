from fastapi import APIRouter, HTTPException
from datetime import datetime
from bson import ObjectId

from app.models.schemas import CompareRequest
from app.services.pdf_parser import parse_pdf_text
from app.services.chunk_service import chunk_paper
from app.services.vector_service import index_paper_chunks
from app.services.extraction_service import extract_fields_for_paper
from app.services.compare_service import compare_papers
from app.db import papers_collection

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.post("/parse/{paper_id}")
def parse_paper(paper_id: str):
    try:
        result = parse_pdf_text(paper_id)
        chunk_paper(paper_id)
        index_paper_chunks(paper_id)
        papers_collection.update_one(
            {"_id": ObjectId(paper_id)},
            {"$set": {"status": "indexed", "indexed_at": datetime.utcnow()}}
        )
        return {"ok": True, **result, "status": "indexed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract/{paper_id}")
def extract_paper(paper_id: str):
    try:
        return extract_fields_for_paper(paper_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compare")
def compare_route(payload: CompareRequest):
    try:
        return compare_papers(payload.paper_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))