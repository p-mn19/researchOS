from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CitationSource(BaseModel):
    paper_id: str
    title: str
    authors: List[str] = []
    year: Optional[int] = None
    section_title: Optional[str] = None
    page: Optional[int] = None
    evidence: Optional[str] = None


class SentencePlan(BaseModel):
    sentence_number: int
    purpose: str
    claim: str
    citation_paper_ids: List[str] = []


class SectionPlanRequest(BaseModel):
    paper_ids: List[str] = Field(..., min_length=1)
    section_type: str = Field(
        ...,
        pattern="^(related_work|methodology)$",
    )
    research_topic: Optional[str] = None
    target_word_count: int = Field(
        default=500,
        ge=150,
        le=1500,
    )


class SectionPlanResponse(BaseModel):
    section_type: str
    section_title: str
    objective: str
    sentence_plan: List[SentencePlan] = []
    recommended_sources: List[CitationSource] = []
    model: str


class DraftSectionRequest(BaseModel):
    paper_ids: List[str] = Field(..., min_length=1)
    section_type: str = Field(
        ...,
        pattern="^(related_work|methodology)$",
    )
    research_topic: Optional[str] = None
    target_word_count: int = Field(
        default=500,
        ge=150,
        le=1500,
    )
    sentence_plan: List[SentencePlan] = []


class DraftSectionResponse(BaseModel):
    section_type: str
    section_title: str
    markdown: str
    citations: List[CitationSource] = []
    model: str