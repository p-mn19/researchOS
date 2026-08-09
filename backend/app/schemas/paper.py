from datetime import datetime
from typing import List, Optional

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

    id: str
    filename: str
    title: str = ""
    authors: List[str] = []
    year: Optional[int] = None
    abstract: str = ""
    uploaded_at: Optional[datetime] = None
    status: str = "uploaded"
    methodology: Optional[str] = None
    dataset: Optional[str] = None
    limitations: Optional[str] = None