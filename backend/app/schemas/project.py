from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict


# -----------------
# Project schemas
# -----------------


class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None
    user_id: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str] = None
    user_id: Optional[str] = None
    paper_ids: List[str] = []
    created_at: datetime
    updated_at: datetime


# -------------------------
# Module 8 — Research gap
# -------------------------


class ResearchIdeaCreate(BaseModel):
    title: str
    problem_statement: str
    hypothesis: Optional[str] = None
    suggested_methodology: Optional[str] = None
    related_paper_ids: List[str] = []
    confidence: Optional[float] = None


class ResearchIdea(ResearchIdeaCreate):
    id: str
    project_id: Optional[str] = None
    created_at: datetime


class ResearchGapSummaryCreate(BaseModel):
    gap_description: str
    key_themes: List[str] = []
    recurring_limitations: List[str] = []
    candidate_methodologies: List[str] = []
    suggested_idea_inputs: List[ResearchIdeaCreate] = []


class ResearchGapSummary(BaseModel):
    id: str
    project_id: Optional[str] = None
    gap_description: str
    key_themes: List[str] = []
    recurring_limitations: List[str] = []
    candidate_methodologies: List[str] = []
    suggested_ideas: List[ResearchIdea] = []
    updated_at: datetime


# -------------------------
# Module 9 — Drafting
# -------------------------


class SectionPlanItemCreate(BaseModel):
    section_name: str
    purpose: str
    key_points: List[str] = []
    target_length_words: Optional[int] = None
    citation_hints: List[str] = []  # paper titles / IDs


class SectionPlanCreate(BaseModel):
    section_name: str
    purpose: str
    outline: List[SectionPlanItemCreate] = []
    recommended_citations: List[Dict[str, Any]] = []
    notes: Optional[str] = None


class SectionPlan(SectionPlanCreate):
    id: Optional[str] = None


class ManuscriptDraftCreate(BaseModel):
    project_id: Optional[str] = None
    title: Optional[str] = None
    section_plans: List[SectionPlanCreate] = []
    content: Optional[Dict[str, str]] = None  # section_name -> text
    citations: Optional[List[Dict[str, Any]]] = None


class ManuscriptDraft(BaseModel):
    id: str
    project_id: Optional[str] = None
    title: Optional[str] = None
    section_plans: List[SectionPlan] = []
    content: Dict[str, str] = {}
    citations: List[Dict[str, Any]] = []
    status: str = "draft"  # draft, revised, final
    created_at: datetime
    updated_at: datetime