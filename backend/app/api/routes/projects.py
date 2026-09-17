from typing import List, Optional


from fastapi import APIRouter, HTTPException, Query


from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ResearchGapSummaryCreate,
    ResearchGapSummary,
    ManuscriptDraftCreate,
    ManuscriptDraft,
)
from app.services.project_service import (
    create_project,
    list_projects,
    get_project_by_id,
    update_project,
    add_papers_to_project,
    create_or_update_research_gap,
    get_research_gap_by_project,
    create_manuscript_draft,
    get_draft_by_id,
    update_draft_content,
)


router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


@router.post(
    "/",
    response_model=ProjectResponse,
)
def create_new_project(data: ProjectCreate):
    return create_project(data)


@router.get(
    "/",
    response_model=List[ProjectResponse],
)
def list_all_projects(user_id: Optional[str] = Query(None)):
    return list_projects(user_id=user_id)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
)
def get_project(project_id: str):
    return get_project_by_id(project_id)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
)
def edit_project(project_id: str, data: ProjectUpdate):
    return update_project(project_id, data)


@router.post(
    "/{project_id}/papers",
    response_model=ProjectResponse,
)
def add_papers_to_existing_project(
    project_id: str,
    paper_ids: List[str],
):
    return add_papers_to_project(project_id, paper_ids)


# -------------------------
# Module 8 — Research gap
# -------------------------


@router.post(
    "/{project_id}/research-gap",
    response_model=ResearchGapSummary,
)
def generate_research_gap(
    project_id: str,
    data: ResearchGapSummaryCreate,
):
    # In a fuller implementation, you would:
    # - Fetch all papers in the project.
    # - Aggregate limitations, research_gap, methodology, etc.
    # - Use an LLM to generate gap_description, themes, and ideas.
    # Here we just store what the client sends.
    return create_or_update_research_gap(project_id, data)


@router.get(
    "/{project_id}/research-gap",
    response_model=Optional[ResearchGapSummary],
)
def get_project_research_gap(project_id: str):
    return get_research_gap_by_project(project_id)


# -------------------------
# Module 9 — Drafting
# -------------------------


@router.post(
    "/drafts",
    response_model=ManuscriptDraft,
)
def create_new_draft(data: ManuscriptDraftCreate):
    return create_manuscript_draft(data)


@router.get(
    "/drafts/{draft_id}",
    response_model=ManuscriptDraft,
)
def get_draft(draft_id: str):
    return get_draft_by_id(draft_id)


@router.patch(
    "/drafts/{draft_id}/section",
    response_model=ManuscriptDraft,
)
def edit_draft_section(
    draft_id: str,
    section_name: str = Query(...),
    content: str = Query(...),
):
    return update_draft_content(draft_id, section_name, content)