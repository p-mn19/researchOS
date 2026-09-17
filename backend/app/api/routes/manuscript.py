from fastapi import APIRouter

from app.schemas.manuscript import (
    DraftSectionRequest,
    DraftSectionResponse,
    SectionPlanRequest,
    SectionPlanResponse,
)
from app.services.manuscript_service import (
    generate_draft_section,
    generate_section_plan,
)


router = APIRouter(
    prefix="/manuscript",
    tags=["Module 9 - Manuscript Composer"],
)


@router.post(
    "/plan",
    response_model=SectionPlanResponse,
)
def create_section_plan(
    payload: SectionPlanRequest,
):
    return generate_section_plan(payload)


@router.post(
    "/generate",
    response_model=DraftSectionResponse,
)
def generate_section(
    payload: DraftSectionRequest,
):
    return generate_draft_section(payload)