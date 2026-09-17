from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict


class PaperStatusUpdate(BaseModel):
    status: str


class PaperCreateResponse(BaseModel):
    id: str
    filename: str
    title: str
    status: str


class PaperResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # Core identity
    id: str
    filename: str
    title: str = ""

    # Bibliographic metadata
    authors: List[str] = []
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None

    # Content summary
    abstract: str = ""
    keywords: List[str] = []

    # Extraction fields (from LLM / OCR pipeline)
    methodology: Optional[str] = None
    dataset: Optional[str] = None
    limitations: Optional[str] = None
    research_gap: Optional[str] = None
    findings: Optional[str] = None
    future_work: Optional[str] = None

    # Structured / parsed sections (optional, for richer drafting later)
    sections: Optional[Dict[str, str]] = None  # e.g. {"introduction": "...", "method": "..."}

    # Citation grounding info (for Module 9)
    # Each citation can be a simple string or a structured dict depending on your pipeline
    citations: Optional[List[Dict[str, Any]]] = None

    # System/metadata
    uploaded_at: Optional[datetime] = None
    status: str = "uploaded"