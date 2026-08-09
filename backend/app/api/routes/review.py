from fastapi import APIRouter, HTTPException

from app.schemas.review import ReviewResponse
from app.services.review_service import generate_review


router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)


@router.post("/{paper_id}", response_model=ReviewResponse)
def create_review(paper_id: str):
    try:
        return generate_review(paper_id)

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Review generation failed: {str(exc)}",
        ) from exc