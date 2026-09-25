from typing import List, Literal

from pydantic import BaseModel


ReviewConcern = Literal[
    "None",
    "Moderate",
    "Major",
    "Critical",
]

ReviewConfidence = Literal[
    "Low",
    "Medium",
    "High",
]


class ReviewDimension(BaseModel):

    id: str

    title: str

    score: str

    concern: ReviewConcern

    confidence: ReviewConfidence

    evidence: str

    suggestion: str


class ReviewResponse(BaseModel):

    paperId: str

    paperTitle: str

    overallScore: str

    overallAssessment: str

    summary: str

    strengths: List[str]

    weaknesses: List[str]

    missingInformation: List[str]

    dimensions: List[ReviewDimension]

    model: str | None = None