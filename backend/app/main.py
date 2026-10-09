from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import compare, ideation, review, workspaces
from app.routers import (
    answers,
    discovery,
    latex_workspace,
    papers,
    reviews,
    search,
)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
)

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

# Paper ingestion, parsing, semantic search, and answers.
app.include_router(papers.router)
app.include_router(search.router)
app.include_router(answers.router)
app.include_router(discovery.router)

# Comparison and reviewer simulation.
app.include_router(compare.router)
app.include_router(review.router)
app.include_router(reviews.router)

# Research workspace, ideation, versioning, and LaTeX compilation.
app.include_router(ideation.router)
app.include_router(workspaces.router)
app.include_router(latex_workspace.router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "ResearchOS backend running",
        "status": "ok",
    }


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "ok": True,
        "service": "researchos-backend",
    }