from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import papers, analysis, search

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers.router)
app.include_router(analysis.router)
app.include_router(search.router)

@app.get("/")
def root():
    return {"app_name": settings.APP_NAME, "environment": settings.APP_ENV}

@app.get("/health")
def health():
    return {"ok": True}