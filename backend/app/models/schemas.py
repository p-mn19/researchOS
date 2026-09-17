from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# --- Module 5: Literature Discovery & Ingestion Schemas ---
class PaperMetadata(BaseModel):
    source: str
    source_id: str
    title: str
    abstract: Optional[str] = "No abstract available"
    authors: List[str] = []
    year: Optional[int] = None
    doi: Optional[str] = None
    pdf_url: Optional[str] = None
    citation_count: Optional[int] = 0
    venue: Optional[str] = None


class DiscoverySearchResponse(BaseModel):
    query: str
    total_found: int
    results: List[PaperMetadata]


# --- Existing Corpus & Search Schemas ---
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


# --- Existing Extraction & Comparison Schemas ---
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