from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


ContentType = Literal[
    "introduction",
    "research_problem",
    "research_objectives",
    "research_questions",
    "hypotheses",
    "related_work",
    "methodology",
    "proposed_framework",
    "experimental_design",
    "evaluation_plan",
    "expected_contributions",
    "limitations_and_scope",
    "abstract_draft",
    "conclusion",
]

GenerationMode = Literal[
    "section",
    "full_paper",
]

PaperSectionKey = Literal[
    "abstract",
    "keywords",
    "introduction",
    "research_problem",
    "research_objectives",
    "research_questions",
    "hypotheses",
    "related_work",
    "proposed_methodology",
    "proposed_framework",
    "experimental_design",
    "evaluation_plan",
    "expected_contributions",
    "limitations_and_scope",
    "conclusion",
]


class WorkspaceIdea(BaseModel):
    """Immutable snapshot of a Module 8 idea selected by the user."""

    title: str = Field(..., min_length=1, max_length=300)
    problem_statement: str = Field(..., min_length=1)
    hypothesis: str = ""
    recommended_methodology: str = ""
    expected_contribution: str = ""
    evidence_paper_ids: List[str] = []


class WorkspaceCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str = ""
    paper_ids: List[str] = Field(..., min_length=1)
    idea: WorkspaceIdea
    research_objective: str = ""


class WorkspaceUpdate(BaseModel):
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=300,
    )
    description: Optional[str] = None
    paper_ids: Optional[List[str]] = None
    idea: Optional[WorkspaceIdea] = None
    research_objective: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: str
    title: str
    description: str = ""
    paper_ids: List[str] = []
    idea: WorkspaceIdea
    research_objective: str = ""
    created_at: datetime
    updated_at: datetime


class FullPaperSectionPlan(BaseModel):
    key: PaperSectionKey
    title: str
    purpose: str
    target_word_count: int = Field(ge=80, le=1200)
    evidence_paper_ids: List[str] = []


class FullPaperOutline(BaseModel):
    paper_title: str
    abstract_target_word_count: int = Field(default=200, ge=100, le=400)
    keywords: List[str] = []
    sections: List[FullPaperSectionPlan] = []
    model: str


class WorkspaceGenerateRequest(BaseModel):
    generation_mode: GenerationMode = "section"

    # Required only when generation_mode is "section".
    content_type: Optional[ContentType] = None

    # Used for individual sections or as the total allocation
    # guide for full-paper orchestration.
    target_word_count: int = Field(
        default=500,
        ge=120,
        le=6000,
    )

    generate_latex: bool = True
    generate_bibtex: bool = True

    # Content body can use internal paper IDs. The final LaTeX
    # file always uses LaTeX citation keys.
    citation_style: Literal["internal", "latex"] = "internal"

    instructions: str = Field(default="", max_length=2000)


class WorkspaceCitation(BaseModel):
    paper_id: str
    title: str
    authors: List[str] = []
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    citation_key: str
    section_title: Optional[str] = None
    page: Optional[int] = None


class WorkspaceSectionResult(BaseModel):
    key: PaperSectionKey
    title: str
    content_markdown: str
    latex_code: str = ""
    citations: List[WorkspaceCitation] = []
    warnings: List[str] = []
    source_chunk_ids: List[str] = []
    status: Literal["generated", "failed"] = "generated"
    error: Optional[str] = None


class WorkspaceGenerationResponse(BaseModel):
    workspace_id: str
    generation_mode: GenerationMode = "section"

    # Single section field. It is populated for generation_mode="section".
    content_type: Optional[ContentType] = None

    title: str
    content_markdown: str
    latex_code: str = ""

    citations: List[WorkspaceCitation] = []
    warnings: List[str] = []
    source_chunk_ids: List[str] = []
    model: str

    # Full-paper fields. They are populated for generation_mode="full_paper".
    outline: Optional[FullPaperOutline] = None
    sections: List[WorkspaceSectionResult] = []
    full_paper_markdown: str = ""
    full_paper_latex: str = ""
    bibtex: str = ""


class WorkspaceVersionCreate(BaseModel):
    generation_mode: GenerationMode = "section"
    content_type: Optional[ContentType] = None
    content_markdown: str = ""
    latex_code: str = ""
    citations: List[WorkspaceCitation] = []
    warnings: List[str] = []
    source_chunk_ids: List[str] = []

    outline: Optional[FullPaperOutline] = None
    sections: List[WorkspaceSectionResult] = []
    full_paper_markdown: str = ""
    full_paper_latex: str = ""
    bibtex: str = ""


class WorkspaceVersionResponse(WorkspaceVersionCreate):
    id: str
    workspace_id: str
    version: int
    created_at: datetime
