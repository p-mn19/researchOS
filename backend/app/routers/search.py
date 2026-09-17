from typing import List

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from app.models.schemas import (
    PaperMetadata,
    SearchRequest,
)
from app.services.discovery_service import (
    LiteratureDiscoveryService,
)
from app.services.search_service import (
    semantic_search,
)


router = APIRouter(
    prefix="/search",
    tags=["search"],
)


discovery_service = (
    LiteratureDiscoveryService()
)


@router.post("/query")
def query_search(
    payload: SearchRequest,
):
    query = payload.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty.",
        )

    try:
        results = semantic_search(
            query=query,
            paper_ids=payload.paper_ids,
            top_k=payload.top_k or 5,
        )

        return {
            "query": query,
            "top_k": payload.top_k or 5,
            "count": len(results),
            "results": results,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(exc)}",
        ) from exc


@router.get(
    "/discovery",
    response_model=List[PaperMetadata],
)
async def discovery_search(
    query: str = Query(
        ...,
        min_length=2,
        max_length=300,
        description="Research topic or keywords",
    ),
    limit: int = Query(
        5,
        ge=1,
        le=10,
        description="Results per academic source",
    ),
):
    query = query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty.",
        )

    try:
        return await discovery_service.search_all(
            query=query,
            limit_per_source=limit,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Discovery search failed: "
                f"{str(exc)}"
            ),
        ) from exc