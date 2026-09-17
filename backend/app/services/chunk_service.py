from datetime import datetime
from typing import Any, Dict, List

from bson import ObjectId
from fastapi import HTTPException

from app.db import (
    chunks_collection,
    papers_collection,
)


CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


def _split_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    text = " ".join(text.split())

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(
            len(text),
            start + chunk_size,
        )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(
            end - overlap,
            start + 1,
        )

    return chunks


def create_paper_chunks(
    paper_id: str,
) -> Dict[str, Any]:
    paper_id = str(paper_id or "").strip()

    if not ObjectId.is_valid(paper_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid paper ID",
        )

    object_id = ObjectId(paper_id)

    paper = papers_collection.find_one(
        {"_id": object_id}
    )

    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Paper not found",
        )

    chunks_collection.delete_many(
        {"paper_id": paper_id}
    )

    pages = paper.get("pages") or []
    documents = []
    chunk_index = 0

    if pages:
        for page in pages:
            page_number = page.get(
                "page_number"
            )

            page_text = page.get("text") or ""

            page_chunks = _split_text(
                page_text
            )

            for chunk_text in page_chunks:
                documents.append(
                    {
                        "paper_id": paper_id,
                        "chunk_index": chunk_index,
                        "text": chunk_text,
                        "section_title": None,
                        "page": page_number,
                        "page_number": page_number,
                        "created_at": datetime.utcnow(),
                    }
                )

                chunk_index += 1

    else:
        full_text = (
            paper.get("raw_text")
            or paper.get("text")
            or ""
        )

        for chunk_text in _split_text(
            full_text
        ):
            documents.append(
                {
                    "paper_id": paper_id,
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "section_title": None,
                    "page": None,
                    "page_number": None,
                    "created_at": datetime.utcnow(),
                }
            )

            chunk_index += 1

    if not documents:
        raise HTTPException(
            status_code=400,
            detail=(
                "Paper has no parsed text "
                "to chunk"
            ),
        )

    chunks_collection.insert_many(
        documents
    )

    papers_collection.update_one(
        {"_id": object_id},
        {
            "$set": {
                "status": "indexed",
                "indexed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return {
        "paper_id": paper_id,
        "chunks_created": len(documents),
    }