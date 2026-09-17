from typing import List

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from app.models.schemas import PaperMetadata
from app.services.discovery_service import (
    LiteratureDiscoveryService,
)


router = APIRouter(
    prefix="/discovery",
    tags=["literature-discovery"],
)


discovery_service = (
    LiteratureDiscoveryService()
)


@router.get(
    "/search",
    response_model=List[PaperMetadata],
)
async def search_global_literature(
    query: str = Query(
        ...,
        min_length=2,
        max_length=300,
    ),
    limit: int = Query(
        5,
        ge=1,
        le=10,
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
                "Global literature search failed: "
                f"{str(exc)}"
            ),
        ) from exc