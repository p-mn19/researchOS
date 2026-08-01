from fastapi import APIRouter, UploadFile, File
from app.services.paper_service import create_paper_record, list_papers, get_paper_by_id

router = APIRouter(prefix="/papers", tags=["papers"])

@router.post("/upload")
def upload_paper(file: UploadFile = File(...)):
    return create_paper_record(file)

@router.get("")
def get_all_papers():
    return list_papers()

@router.get("/{paper_id}")
def get_paper(paper_id: str):
    return get_paper_by_id(paper_id)