from fastapi import APIRouter, HTTPException
from app.models.schemas import SearchRequest
from app.services.search_service import semantic_search

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/query")
def query_search(payload: SearchRequest):
    try:
        return semantic_search(payload.query, payload.paper_ids, payload.top_k or 5)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))