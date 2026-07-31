from typing import Optional, List
from pydantic import BaseModel


class PaperStatusUpdate(BaseModel):
    status: str


class PaperCreateResponse(BaseModel):
    message: str
    paper_id: str
    status: str
    filename: str


class PaperResponse(BaseModel):
    id: str
    original_filename: str
    stored_filename: str
    file_path: str
    content_type: Optional[str] = None
    file_size: Optional[int] = None

    title: Optional[str] = None
    authors: Optional[List[str]] = None
    publication_year: Optional[int] = None
    abstract: Optional[str] = None
    keywords: Optional[List[str]] = None
    references: Optional[List[str]] = None

    status: str
    error_message: Optional[str] = None
    created_at: str
    updated_at: str