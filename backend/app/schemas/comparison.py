from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CompareRequest(BaseModel):
    paper_ids: List[str] = Field(..., min_length=2, description="Paper IDs to compare")


class CompareRow(BaseModel):
    field: str
    values: Dict[str, str]


class CompareResponse(BaseModel):
    rows: List[CompareRow]
    paper_map: Optional[Dict[str, str]] = None