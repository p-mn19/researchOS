from fastapi import APIRouter, HTTPException

from app.models.schemas import SearchRequest
from app.services.search_service import semantic_search


router = APIRouter(
    prefix="/search",
    tags=["search"],
)


@router.post("/query")
def query_search(payload: SearchRequest):
    query = payload.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty.",
        )

    try:
        results = semantic_search(
            query=query,
            paper_ids=payload.paper_ids,
            top_k=payload.top_k or 5,
        )

        return {
            "query": query,
            "results": results,
            "count": len(results),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Semantic search failed: {str(exc)}",
        ) from exc