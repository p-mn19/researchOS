from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException, UploadFile

from app.db.session import papers_collection
from app.models.paper import PaperStatus, VALID_STATUS_TRANSITIONS
from app.utils.file_storage import save_pdf_locally

def serialize_paper(doc):
    return {
        "id": str(doc["_id"]),
        "original_filename": doc.get("original_filename"),
        "stored_filename": doc.get("stored_filename"),
        "file_path": doc.get("file_path"),
        "content_type": doc.get("content_type"),
        "file_size": doc.get("file_size"),
        "title": doc.get("title"),
        "authors": doc.get("authors", []),
        "publication_year": doc.get("publication_year"),
        "abstract": doc.get("abstract"),
        "keywords": doc.get("keywords", []),
        "references": doc.get("references", []),
        "status": doc.get("status"),
        "error_message": doc.get("error_message"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }

def create_paper_record(file: UploadFile):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    stored_filename, file_path, file_size = save_pdf_locally(file)
    now = datetime.utcnow().isoformat()

    paper_doc = {
        "original_filename": file.filename,
        "stored_filename": stored_filename,
        "file_path": file_path,
        "content_type": file.content_type,
        "file_size": file_size,

        "title": None,
        "authors": [],
        "publication_year": None,
        "abstract": None,
        "keywords": [],
        "references": [],

        "status": PaperStatus.uploaded.value,
        "error_message": None,
        "created_at": now,
        "updated_at": now
    }

    result = papers_collection.insert_one(paper_doc)

    return {
        "message": "Paper uploaded successfully",
        "paper_id": str(result.inserted_id),
        "status": PaperStatus.uploaded.value,
        "filename": file.filename
    }


def get_all_papers():
    papers = papers_collection.find().sort("created_at", -1)
    return [serialize_paper(p) for p in papers]


def get_paper_by_id(paper_id: str):
    if not ObjectId.is_valid(paper_id):
        raise HTTPException(status_code=400, detail="Invalid paper ID")

    paper = papers_collection.find_one({"_id": ObjectId(paper_id)})
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    return serialize_paper(paper)


def update_paper_status(paper_id: str, new_status: str):
    if not ObjectId.is_valid(paper_id):
        raise HTTPException(status_code=400, detail="Invalid paper ID")

    paper = papers_collection.find_one({"_id": ObjectId(paper_id)})
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    current_status = paper["status"]

    if new_status not in [status.value for status in PaperStatus]:
        raise HTTPException(status_code=400, detail="Invalid status")

    allowed_next = VALID_STATUS_TRANSITIONS.get(current_status, [])
    if new_status not in allowed_next:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition from '{current_status}' to '{new_status}'"
        )

    papers_collection.update_one(
        {"_id": ObjectId(paper_id)},
        {
            "$set": {
                "status": new_status,
                "updated_at": datetime.utcnow().isoformat()
            }
        }
    )

    updated_paper = papers_collection.find_one({"_id": ObjectId(paper_id)})
    return serialize_paper(updated_paper)