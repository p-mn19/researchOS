from fastapi import APIRouter, HTTPException

from app.services.chunk_service import (
    create_paper_chunks,
)
from app.services.extraction_service import (
    extract_paper_content,
)
from app.services.paper_service import (
    get_paper_by_id,
)
from app.services.parser_service import (
    parse_pdf_text,
)


router = APIRouter(
    prefix="/papers",
    tags=["analysis"],
)


@router.post("/{paper_id}/parse")
def parse_paper_route(paper_id: str):
    try:
        parse_result = parse_pdf_text(paper_id)
        chunk_result = create_paper_chunks(paper_id)

        return {
            **parse_result,
            **chunk_result,
            "status": "indexed",
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Parsing and indexing failed: {str(exc)}",
        ) from exc


@router.post("/{paper_id}/extract")
def extract_paper_route(paper_id: str):
    try:
        # Always parse again so the latest text is available.
        parse_pdf_text(paper_id)

        # Create MongoDB chunks for search and RAG.
        chunk_result = create_paper_chunks(paper_id)

        # Fetch the updated paper after parsing.
        paper = get_paper_by_id(paper_id)

        if not paper:
            raise HTTPException(
                status_code=404,
                detail="Paper not found after parsing",
            )

        result = extract_paper_content(
            paper_id=paper_id,
            paper=paper,
        )

        return {
            "paper_id": paper_id,
            "status": "extracted",
            "chunks_created": chunk_result[
                "chunks_created"
            ],
            "extraction": result,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(exc)}",
        ) from exc