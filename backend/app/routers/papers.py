from typing import List

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)

from app.db import extractions_collection
from app.schemas.paper import (
    PaperCreateResponse,
    PaperResponse,
    PaperStatusUpdate,
)
from app.schemas.search import SearchRequest
from app.services.chunk_service import (
    create_paper_chunks,
)
from app.services.extraction_service import (
    extract_paper_content,
)
from app.services.paper_service import (
    create_paper_record,
    delete_paper,
    get_all_papers,
    get_paper_by_id,
    update_paper_status,
)
from app.services.parser_service import (
    parse_pdf_text,
)
from app.services.search_service import (
    semantic_search,
)


router = APIRouter(
    prefix="/papers",
    tags=["papers"],
)


@router.post(
    "/upload",
    response_model=PaperCreateResponse,
)
def upload_paper(
    file: UploadFile = File(...),
):
    return create_paper_record(file)


@router.get(
    "/",
    response_model=List[PaperResponse],
)
def list_papers():
    return get_all_papers()


@router.get(
    "/{paper_id}",
    response_model=PaperResponse,
)
def get_paper(paper_id: str):
    return get_paper_by_id(paper_id)


@router.delete("/{paper_id}")
def remove_paper(
    paper_id: str,
):
    try:
        return delete_paper(
            paper_id
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Paper deletion failed: "
                f"{str(exc)}"
            ),
        ) from exc


@router.post("/{paper_id}/parse")
def parse_paper(paper_id: str):
    try:
        parse_result = parse_pdf_text(
            paper_id
        )

        chunk_result = create_paper_chunks(
            paper_id
        )

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
            detail=(
                "Parsing and indexing failed: "
                f"{str(exc)}"
            ),
        ) from exc


@router.post("/{paper_id}/extract")
def extract_paper(paper_id: str):
    try:
        parse_pdf_text(paper_id)

        chunk_result = create_paper_chunks(
            paper_id
        )

        fields = extract_paper_content(
            paper_id=paper_id
        )

        return {
            "paper_id": paper_id,
            "status": "extracted",
            "chunks_created": (
                chunk_result["chunks_created"]
            ),
            "extraction": fields,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Extraction failed: "
                f"{str(exc)}"
            ),
        ) from exc


@router.get("/{paper_id}/extraction")
def get_paper_extraction(paper_id: str):
    extraction = extractions_collection.find_one(
        {"paper_id": paper_id},
        {"_id": 0},
    )

    if extraction is None:
        raise HTTPException(
            status_code=404,
            detail="Extraction not found",
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
            detail=(
                "Paper search failed: "
                f"{str(exc)}"
            ),
        ) from exc


@router.patch(
    "/{paper_id}/status",
    response_model=PaperResponse,
)
def change_paper_status(
    paper_id: str,
    payload: PaperStatusUpdate,
):
    return update_paper_status(
        paper_id,
        payload.status,
    )