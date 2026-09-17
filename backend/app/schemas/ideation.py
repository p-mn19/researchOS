from typing import List, Optional

from pydantic import BaseModel, Field


class IdeationRequest(BaseModel):
    paper_ids: List[str] = Field(
        ...,
        min_length=1,
        description="IDs of extracted papers to analyze",
    )
    topic: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional research topic or direction",
    )
    idea_count: int = Field(
        default=3,
        ge=1,
        le=5,
    )


class EvidencePaper(BaseModel):
    paper_id: str
    title: str
    limitation: Optional[str] = None
    future_work: Optional[str] = None
    research_gap: Optional[str] = None
    methodology: Optional[str] = None


class ResearchIdea(BaseModel):
    title: str
    problem_statement: str
    hypothesis: str
    recommended_methodology: str
    expected_contribution: str
    evidence_paper_ids: List[str] = []


class IdeationResponse(BaseModel):
    corpus_size: int
    topic: Optional[str] = None
    recurring_limitations: List[str] = []
    research_gaps: List[str] = []
    recommended_methodologies: List[str] = []
    ideas: List[ResearchIdea] = []
    evidence_papers: List[EvidencePaper] = []
    model: str