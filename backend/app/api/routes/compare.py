from fastapi import APIRouter, HTTPException

from app.schemas.comparison import (
    CompareRequest,
    CompareResponse,
)
from app.services.compare_service import compare_papers


router = APIRouter(
    prefix="/compare",
    tags=["compare"],
)


@router.post("", response_model=CompareResponse)
def compare_selected_papers(payload: CompareRequest):
    try:
        return compare_papers(payload.paper_ids)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Comparison failed: {str(exc)}",
        ) from exc