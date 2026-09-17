from fastapi import APIRouter, HTTPException, Query
from typing import List

# --- Existing Imports ---
from app.services.search_service import semantic_search

# --- Schema Imports (Adjust path if needed based on your structure) ---
from app.models.schemas import (
    SearchRequest, 
    SearchResponse, 
    PaperMetadata
)

# --- New Discovery Service Import ---
from app.services.discovery_service import LiteratureDiscoveryService

router = APIRouter(
    prefix="/search",
    tags=["search"],
)

# Initialize the discovery service
discovery_service = LiteratureDiscoveryService()


# ==========================================
# 1. LOCAL SEMANTIC SEARCH (Existing)
# ==========================================
@router.post("/query", response_model=SearchResponse)
def global_search(payload: SearchRequest):
    try:
        query = payload.query.strip()

        results = semantic_search(
            query=query,
            paper_ids=payload.paper_ids,
            top_k=payload.top_k,
        )

        # Retaining your exact original return structure
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


# ==========================================
# 2. GLOBAL LITERATURE DISCOVERY (New Module 5)
# ==========================================
@router.get("/discovery", response_model=List[PaperMetadata])
async def search_global_literature(
    query: str = Query(..., description="Research topic or keywords"),
    limit: int = Query(5, ge=1, le=25, description="Results per academic API source")
):
    """
    Simultaneously queries OpenAlex and arXiv, returning normalized, 
    deduplicated academic papers ready for corpus ingestion.
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