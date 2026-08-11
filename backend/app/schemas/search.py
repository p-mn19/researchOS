from typing import List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    paper_ids: Optional[List[str]] = None
    top_k: int = Field(default=5, ge=1, le=20)


class SearchHit(BaseModel):
    id: str
    paper_id: str
    paper_title: str
    filename: Optional[str] = None
    section_title: Optional[str] = None
    page: Optional[int] = None
    text: str
    score: float


class SearchResponse(BaseModel):
    query: str
    top_k: int
    count: int
    results: List[SearchHit]