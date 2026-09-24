from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import compare, review
from app.api.routes import ideation, workspaces
from app.routers import answers, papers, search, discovery,latex_workspace


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


app.include_router(papers.router)
app.include_router(search.router)
app.include_router(answers.router)
app.include_router(discovery.router)
app.include_router(compare.router)
app.include_router(review.router)

# New standalone modules
app.include_router(ideation.router)
app.include_router(workspaces.router)
app.include_router(latex_workspace.router)

@app.get("/")
def root():
    return {
        "message": "ResearchOS backend running",
        "status": "ok",
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "researchos-backend",
    }