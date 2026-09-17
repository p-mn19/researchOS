from fastapi import APIRouter

from app.schemas.ideation import (
    IdeationRequest,
    IdeationResponse,
)
from app.services.ideation_service import generate_ideation


router = APIRouter(
    prefix="/ideation",
    tags=["Module 8 - Research Gap & Ideation"],
)


@router.post(
    "/analyze",
    response_model=IdeationResponse,
)
def analyze_research_gaps(
    payload: IdeationRequest,
):
    return generate_ideation(payload)