from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.db import extractions_collection
from app.schemas.paper import (
    PaperCreateResponse,
    PaperResponse,
    PaperStatusUpdate,
)
from app.schemas.search import SearchRequest
from app.services.extraction_service import extract_fields_for_paper
from app.services.paper_service import (
    create_paper_record,
    get_all_papers,
    get_paper_by_id,
    update_paper_status,
)
from app.services.pdf_parser import parse_pdf_text
from app.services.search_service import semantic_search


router = APIRouter(
    prefix="/papers",
    tags=["papers"],
)


@router.post("/upload", response_model=PaperCreateResponse)
def upload_paper(file: UploadFile = File(...)):
    return create_paper_record(file)


@router.get("/", response_model=List[PaperResponse])
def list_papers():
    return get_all_papers()


@router.get("/{paper_id}", response_model=PaperResponse)
def get_paper(paper_id: str):
    return get_paper_by_id(paper_id)


@router.post("/{paper_id}/parse")
def parse_paper(paper_id: str):
    return parse_pdf_text(paper_id)


@router.post("/{paper_id}/extract")
def extract_paper(paper_id: str):
    return extract_fields_for_paper(paper_id)


@router.get("/{paper_id}/extraction")
def get_paper_extraction(paper_id: str):
    extraction = extractions_collection.find_one(
        {"paper_id": paper_id},
        {"_id": 0},
    )

    return extraction


@router.post("/{paper_id}/search")
def search_inside_paper(
    paper_id: str,
    payload: SearchRequest,
):
    try:
        results = semantic_search(
            query=payload.query,
            paper_ids=[paper_id],
            top_k=payload.top_k,
        )

        return {
            "query": payload.query,
            "top_k": payload.top_k,
            "count": len(results),
            "results": results,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Paper search failed: {str(exc)}",
        ) from exc


@router.patch("/{paper_id}/status", response_model=PaperResponse)
def change_paper_status(
    paper_id: str,
    payload: PaperStatusUpdate,
):
    return update_paper_status(paper_id, payload.status)