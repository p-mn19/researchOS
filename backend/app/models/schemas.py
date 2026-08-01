from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class PaperResponse(BaseModel):
    id: str
    filename: str
    title: Optional[str] = ""
    status: str

class SearchRequest(BaseModel):
    query: str
    paper_ids: Optional[List[str]] = None
    top_k: Optional[int] = 5

class SearchResultItem(BaseModel):
    paper_id: str
    chunk_id: str
    section_title: Optional[str] = ""
    page_number: Optional[int] = None
    text: str
    score: float

class SearchResponse(BaseModel):
    answer: str
    results: List[SearchResultItem]

class ExtractionResponse(BaseModel):
    paper_id: str
    objective: Optional[str] = ""
    methodology: Optional[str] = ""
    dataset: Optional[str] = ""
    evaluation_metric: Optional[str] = ""
    limitations: Optional[str] = ""
    future_work: Optional[str] = ""

class CompareRequest(BaseModel):
    paper_ids: List[str]

class CompareResponse(BaseModel):
    rows: List[Dict[str, Any]]