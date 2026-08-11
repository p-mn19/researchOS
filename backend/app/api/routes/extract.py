from fastapi import APIRouter, HTTPException
from bson import ObjectId

from app.db import papers_collection
from app.services.pdf_parser import parse_pdf_text
from app.services.extraction_service import extract_paper_content


router = APIRouter(prefix="/papers", tags=["extraction"])


@router.post("/{paper_id}/extract")
def extract_paper(paper_id: str):
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

    # Read the status from the database, not from the frontend.
    status = str(
        paper.get("status") or ""
    ).strip().lower()

    # Automatically parse papers that have not been parsed yet.
    if status != "parsed":
        try:
            parse_pdf_text(paper_id)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Paper parsing failed: {str(exc)}",
            ) from exc

        # Always fetch the updated document after parsing.
        paper = papers_collection.find_one(
            {"_id": object_id}
        )

        if not paper:
            raise HTTPException(
                status_code=404,
                detail="Paper disappeared after parsing",
            )

        status = str(
            paper.get("status") or ""
        ).strip().lower()

    if status != "parsed":
        raise HTTPException(
            status_code=400,
            detail=(
                "Paper could not be parsed. "
                f"Current status: {status or 'unknown'}"
            ),
        )

    try:
        result = extract_paper_content(
            paper_id=paper_id,
            paper=paper,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(exc)}",
        ) from exc

    return result