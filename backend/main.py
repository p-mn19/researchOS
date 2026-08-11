from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.compare import router as compare_router
from app.api.routes.papers import router as papers_router
from app.api.routes.review import router as review_router
from app.api.routes.search import router as search_router


app = FastAPI(
    title="ResearchOS Backend",
    version="1.0.0",
    description="Backend API for the ResearchOS academic research assistant.",
)


# Allow requests from the Next.js development server.
# Keep credentials enabled only with explicit origins, not '*'.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register all application routers.
app.include_router(papers_router)
app.include_router(search_router)
app.include_router(compare_router)
app.include_router(review_router)


@app.get("/", tags=["system"])
def root():
    return {
        "message": "ResearchOS backend running",
        "status": "ok",
        "version": "1.0.0",
    }


@app.get("/health", tags=["system"])
def health():
    return {
        "ok": True,
        "service": "researchos-backend",
    }