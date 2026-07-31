from fastapi import FastAPI
from app.api.routes.papers import router as papers_router

app = FastAPI(title="ResearchOS Backend")

app.include_router(papers_router)


@app.get("/")
def root():
    return {
        "message": "ResearchOS backend is running",
        "status_pipeline": ["uploaded", "parsed", "indexed", "extracted"]
    }