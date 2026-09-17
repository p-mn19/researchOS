from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict


# -----------------------------
# Basic extraction from a paper
# -----------------------------


class ExtractionResult(BaseModel):
    """Structured extraction for a single paper."""

    paper_id: str

    # Core fields already used
    objective: Optional[str] = None
    methodology: Optional[str] = None
    dataset: Optional[str] = None
    evaluation_metric: Optional[str] = None
    limitations: Optional[str] = None
    future_work: Optional[str] = None

    # Additional fields useful for Modules 8 & 9
    research_gap: Optional[str] = None
    findings: Optional[str] = None
    keywords: List[str] = []

    # Optional structured sections (for richer drafting later)
    sections: Optional[Dict[str, str]] = None  # e.g. {"introduction": "...", "method": "..."}

    # Citation-related fields (for Module 9 grounding)
    doi: Optional[str] = None
    url: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = None

    updated_at: Optional[datetime] = None


# ---------------------------------
# Module 8 — Research gap & ideation
# ---------------------------------


class ResearchIdea(BaseModel):
    """A single AI-suggested research idea derived from the corpus."""

    id: str
    title: str
    problem_statement: str
    hypothesis: Optional[str] = None
    suggested_methodology: Optional[str] = None
    related_limitations: List[str] = []  # paper_ids or short descriptions
    confidence: Optional[float] = None  # 0–1 if you compute it
    created_at: datetime


class ResearchGapSummary(BaseModel):
    """Corpus-level research gap summary for Module 8."""

    project_id: Optional[str] = None  # if tied to a project
    gap_description: str
    key_themes: List[str] = []
    recurring_limitations: List[str] = []
    candidate_methodologies: List[str] = []
    suggested_ideas: List[ResearchIdea] = []
    updated_at: datetime


# ------------------------------------
# Module 9 — Manuscript drafting & plan
# ------------------------------------


class SectionPlanItem(BaseModel):
    """One planned section in a manuscript draft."""

    section_name: str  # e.g. "Related Work", "Methodology"
    purpose: str
    key_points: List[str] = []
    target_length_words: Optional[int] = None
    citation_hints: List[str] = []  # e.g. paper titles or IDs to cite


class SectionPlan(BaseModel):
    """Structured plan for a manuscript section."""

    section_name: str
    purpose: str
    outline: List[SectionPlanItem] = []
    recommended_citations: List[Dict[str, Any]] = []  # paper metadata
    notes: Optional[str] = None


class ManuscriptDraft(BaseModel):
    """A draft manuscript section or full paper."""

    id: str
    project_id: Optional[str] = None
    title: Optional[str] = None
    section_plans: List[SectionPlan] = []
    content: Dict[str, str] = {}  # section_name -> text
    citations: List[Dict[str, Any]] = []  # grounded citations used
    status: str = "draft"  # draft, revised, final
    created_at: datetime
    updated_at: datetime