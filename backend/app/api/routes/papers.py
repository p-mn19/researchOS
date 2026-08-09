from typing import List

from fastapi import APIRouter, File, UploadFile

from app.schemas.paper import (
    PaperCreateResponse,
    PaperResponse,
    PaperStatusUpdate,
)
from app.services.paper_service import (
    create_paper_record,
    get_all_papers,
    get_paper_by_id,
    update_paper_status,
)


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


@router.patch("/{paper_id}/status", response_model=PaperResponse)
def change_paper_status(
    paper_id: str,
    payload: PaperStatusUpdate,
):
    return update_paper_status(paper_id, payload.status)