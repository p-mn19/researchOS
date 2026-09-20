from datetime import datetime
from typing import List, Literal, Optional

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


class WorkspaceIdea(BaseModel):
    """
    Immutable snapshot of a candidate research idea selected
    from Module 8 — Research Gap & Ideation.
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=300,
    )

    problem_statement: str = Field(
        ...,
        min_length=1,
    )

    hypothesis: str = ""
    recommended_methodology: str = ""
    expected_contribution: str = ""

    evidence_paper_ids: List[str] = Field(
        default_factory=list,
    )


class WorkspaceCreate(BaseModel):
    """
    Creates a reusable research workspace with selected evidence
    papers and one selected Module 8 idea snapshot.
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=300,
    )

    description: str = ""

    paper_ids: List[str] = Field(
        ...,
        min_length=1,
    )

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

    paper_ids: List[str] = Field(
        default_factory=list,
    )

    idea: WorkspaceIdea

    research_objective: str = ""

    created_at: datetime
    updated_at: datetime


class WorkspaceGenerateRequest(BaseModel):
    """
    Request to generate one research workspace section.

    The system currently supports single-section generation only.
    """

    content_type: ContentType

    target_word_count: int = Field(
        default=500,
        ge=120,
        le=1800,
    )

    generate_latex: bool = True

    citation_style: Literal[
        "internal",
        "latex",
    ] = "internal"

    instructions: str = Field(
        default="",
        max_length=1500,
    )


class WorkspaceCitation(BaseModel):
    """
    Maps a selected paper to both an internal paper ID and a
    generated LaTeX citation key.
    """

    paper_id: str

    title: str

    authors: List[str] = Field(
        default_factory=list,
    )

    year: Optional[int] = None

    venue: Optional[str] = None

    doi: Optional[str] = None

    citation_key: str

    section_title: Optional[str] = None

    page: Optional[int] = None


class WorkspaceGenerationResponse(BaseModel):
    """
    Response for a single generated workspace section.
    """

    workspace_id: str

    content_type: ContentType

    title: str

    content_markdown: str

    latex_code: str = ""

    citations: List[WorkspaceCitation] = Field(
        default_factory=list,
    )

    warnings: List[str] = Field(
        default_factory=list,
    )

    source_chunk_ids: List[str] = Field(
        default_factory=list,
    )

    model: str


class WorkspaceVersionCreate(BaseModel):
    """
    Stores an editable generated section as a version in MongoDB.
    """

    content_type: ContentType

    content_markdown: str = ""

    latex_code: str = ""

    citations: List[WorkspaceCitation] = Field(
        default_factory=list,
    )

    warnings: List[str] = Field(
        default_factory=list,
    )

    source_chunk_ids: List[str] = Field(
        default_factory=list,
    )


class WorkspaceVersionResponse(
    WorkspaceVersionCreate,
):
    id: str

    workspace_id: str

    version: int

    created_at: datetime