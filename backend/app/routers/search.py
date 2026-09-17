from fastapi import APIRouter, HTTPException, Query
from typing import List

from app.models.schemas import PaperMetadata
from app.services.discovery_service import LiteratureDiscoveryService

# Create the router instance
router = APIRouter(
    prefix="/search",
    tags=["search"],
)

discovery_service = LiteratureDiscoveryService()


@router.get("/discovery", response_model=List[PaperMetadata])
async def search_global_literature(
    query: str = Query(..., description="Research topic or keywords"),
    limit: int = Query(5, ge=1, le=25, description="Results per academic API source")
):
    """
    Queries OpenAlex and arXiv simultaneously, returning deduplicated academic papers.
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    try:
        results = await discovery_service.search_all(query=query, limit_per_source=limit)
        return results
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Discovery search failed: {str(exc)}",
        ) from exc