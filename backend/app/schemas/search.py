from fastapi import APIRouter, HTTPException
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import semantic_search

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/query", response_model=SearchResponse)
def query_search(payload: SearchRequest):
    try:
        results = semantic_search(payload.query, payload.paper_ids, payload.top_k or 5)
        return {
            "query": payload.query,
            "top_k": payload.top_k or 5,
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))