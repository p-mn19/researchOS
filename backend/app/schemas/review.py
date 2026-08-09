from typing import List

from pydantic import BaseModel


class ReviewDimension(BaseModel):
    id: str
    title: str
    score: str
    concern: str
    evidence: str
    suggestion: str


class ReviewResponse(BaseModel):
    paperId: str
    paperTitle: str
    overallScore: str
    summary: str
    dimensions: List[ReviewDimension]