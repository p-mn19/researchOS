from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.review import ReviewResponse
from app.services.review_service import generate_review


router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)


@router.post(
    "/{paper_id}",
    response_model=ReviewResponse,
)
def generate_paper_review(
    paper_id: str,
) -> ReviewResponse:
    """Generate an evidence-grounded review for one uploaded paper."""
    try:
        result = generate_review(paper_id)
        return ReviewResponse(**result)

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Review generation failed: "
                f"{str(exc)}"
            ),
        ) from exc