from fastapi import APIRouter, HTTPException

from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import semantic_search


router = APIRouter(
    prefix="/search",
    tags=["search"],
)


@router.post("/query", response_model=SearchResponse)
def global_search(payload: SearchRequest):
    try:
        query = payload.query.strip()

        results = semantic_search(
            query=query,
            paper_ids=payload.paper_ids,
            top_k=payload.top_k,
        )

        return {
            "query": query,
            "top_k": payload.top_k,
            "count": len(results),
            "results": results,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(exc)}",
        ) from exc