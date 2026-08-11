from typing import Dict, List

from pydantic import BaseModel, Field


class CompareRequest(BaseModel):
    paper_ids: List[str] = Field(..., min_length=2, max_length=4)


class CompareRow(BaseModel):
    field: str
    values: Dict[str, str]


class CompareResponse(BaseModel):
    rows: List[CompareRow]
    paper_map: Dict[str, str]