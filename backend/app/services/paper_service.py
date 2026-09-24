from datetime import datetime
from pathlib import Path
import re
import shutil
import uuid

from bson import ObjectId
from fastapi import HTTPException, UploadFile
from PyPDF2 import PdfReader

from app.config import STORAGE_DIR
from app.db import (
    chunks_collection,
    extractions_collection,
    papers_collection,
)
from app.services.vector_service import (
    delete_paper_vectors,
)


STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def _safe_filename(filename: str) -> str:
    original_name = Path(filename).name
    stem = Path(original_name).stem
    suffix = Path(original_name).suffix.lower()

    safe_stem = re.sub(
        r"[^a-zA-Z0-9._-]",
        "_",
        stem,
    )

    return (
        f"{uuid.uuid4().hex}_"
        f"{safe_stem}"
        f"{suffix}"
    )


def _extract_pdf_metadata(
    file_path: Path,
    fallback_filename: str,
):
    title = ""
    year = None
    authors = []

    try:
        reader = PdfReader(str(file_path))
        metadata = reader.metadata or {}

        raw_title = (
            getattr(metadata, "title", None)
            or metadata.get("/Title")
        )

        raw_author = (
            getattr(metadata, "author", None)
            or metadata.get("/Author")
        )

        if raw_title and str(raw_title).strip():
            title = str(raw_title).strip()

        if raw_author and str(raw_author).strip():
            authors = [
                author.strip()
                for author in str(raw_author).split(",")
                if author.strip()
            ]

    except Exception:
        pass

    if not title:
        title = (
            Path(fallback_filename)
            .stem
            .replace("_", " ")
        )

    return title, authors, year


def _validate_object_id(
    paper_id: str,
) -> ObjectId:
    paper_id = str(
        paper_id or ""
    ).strip()

    if (
        not paper_id
        or not ObjectId.is_valid(paper_id)
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid paper ID: "
                f"{paper_id!r}"
            ),
        )

    return ObjectId(paper_id)


def _serialize_paper(
    document: dict,
) -> dict:
    return {
        "id": str(document["_id"]),
        "filename": document.get(
            "filename",
            "",
        ),
        "stored_filename": document.get(
            "stored_filename",
            "",
        ),
        "filepath": document.get(
            "filepath",
            "",
        ),
        "title": document.get(
            "title",
            "",
        ),
        "authors": document.get(
            "authors",
            [],
        ),
        "year": document.get(
            "year",
        ),
        "abstract": document.get(
            "abstract",
            "",
        ),
        "keywords": document.get(
            "keywords",
            [],
        ),
        "references": document.get(
            "references",
            [],
        ),
        "status": document.get(
            "status",
            "uploaded",
        ),
        "raw_text": document.get(
            "raw_text",
            "",
        ),
        "text": document.get(
            "text",
            "",
        ),
        "pages": document.get(
            "pages",
            [],
        ),

        # Extraction fields
        "methodology": document.get(
            "methodology",
        ),
        "dataset": document.get(
            "dataset",
        ),
        "limitations": document.get(
            "limitations",
        ),
        "research_gap": document.get(
            "research_gap",
        ),
        "findings": document.get(
            "findings",
        ),
        "future_work": document.get(
            "future_work",
        ),
        "objective": document.get(
            "objective",
        ),

        # Timestamps
        "uploaded_at": document.get(
            "uploaded_at",
        ),
        "parsed_at": document.get(
            "parsed_at",
        ),
        "indexed_at": document.get(
            "indexed_at",
        ),
        "extracted_at": document.get(
            "extracted_at",
        ),
        "updated_at": document.get(
            "updated_at",
        ),
    }


def create_paper_record(
    file: UploadFile,
):
    filename = file.filename or ""

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed",
        )

    stored_filename = _safe_filename(
        filename
    )

    save_path = (
        STORAGE_DIR /
        stored_filename
    )

    try:
        with open(
            save_path,
            "wb",
        ) as buffer:
            shutil.copyfileobj(
                file.file,
                buffer,
            )

    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Could not save uploaded file: "
                f"{str(exc)}"
            ),
        ) from exc

    title, authors, year = (
        _extract_pdf_metadata(
            save_path,
            filename,
        )
    )

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

    result = papers_collection.insert_one(
        paper_document
    )

    return {
        "id": str(
            result.inserted_id
        ),
        "filename": filename,
        "title": title,
        "status": "uploaded",
    }


def list_papers():
    documents = (
        papers_collection
        .find()
        .sort(
            "uploaded_at",
            -1,
        )
    )

    return [
        _serialize_paper(document)
        for document in documents
    ]


def get_all_papers():
    return list_papers()


def get_paper_by_id(
    paper_id: str,
):
    object_id = _validate_object_id(
        paper_id
    )

    paper = papers_collection.find_one(
        {"_id": object_id}
    )

    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Paper not found",
        )

    return _serialize_paper(paper)


def update_paper_status(
    paper_id: str,
    status: str,
):
    allowed_statuses = {
        "uploaded",
        "parsed",
        "indexed",
        "extracted",
    }

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid status: "
                f"{status}"
            ),
        )

    object_id = _validate_object_id(
        paper_id
    )

    result = papers_collection.update_one(
        {"_id": object_id},
        {
            "$set": {
                "status": status,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Paper not found",
        )

    return get_paper_by_id(
        paper_id
    )


def delete_paper(
    paper_id: str,
):
    """
    Permanently remove a paper and all
    associated ResearchOS data.

    Deletes:
    - ChromaDB vector embeddings
    - MongoDB chunks
    - MongoDB extraction
    - Stored PDF
    - MongoDB paper record
    """

    object_id = _validate_object_id(
        paper_id
    )

    paper = papers_collection.find_one(
        {"_id": object_id}
    )

    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Paper not found",
        )

    paper_id_string = str(
        paper["_id"]
    )

    # -----------------------------------------------------
    # Delete vector embeddings
    # -----------------------------------------------------

    try:
        vector_result = (
            delete_paper_vectors(
                paper_id_string
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Could not delete paper "
                "vectors: "
                f"{str(exc)}"
            ),
        ) from exc

    # -----------------------------------------------------
    # Delete MongoDB chunks
    # -----------------------------------------------------

    chunks_result = (
        chunks_collection.delete_many(
            {
                "paper_id": paper_id_string
            }
        )
    )

    # -----------------------------------------------------
    # Delete extraction
    # -----------------------------------------------------

    extraction_result = (
        extractions_collection.delete_many(
            {
                "paper_id": paper_id_string
            }
        )
    )

    # -----------------------------------------------------
    # Delete stored PDF
    # -----------------------------------------------------

    filepath = paper.get(
        "filepath"
    )

    file_deleted = False

    if filepath:
        try:
            file_path = Path(filepath)

            if file_path.exists():
                file_path.unlink()
                file_deleted = True

        except OSError as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Paper data was processed "
                    "but the stored PDF could not "
                    "be deleted: "
                    f"{str(exc)}"
                ),
            ) from exc

    # -----------------------------------------------------
    # Delete paper record
    # -----------------------------------------------------

    paper_result = (
        papers_collection.delete_one(
            {"_id": object_id}
        )
    )

    if paper_result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Paper could not be deleted",
        )

    return {
        "paper_id": paper_id_string,
        "message": "Paper deleted successfully",
        "vectors_deleted": vector_result.get(
            "deleted",
            0,
        ),
        "chunks_deleted": (
            chunks_result.deleted_count
        ),
        "extraction_deleted": (
            extraction_result.deleted_count
        ),
        "file_deleted": file_deleted,
    }