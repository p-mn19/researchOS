from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.papers import router as papers_router
from app.api.routes.review import router as review_router
from app.api.routes.search import router as search_router

app = FastAPI(title="ResearchOS Backend")

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

app.include_router(papers_router)
app.include_router(search_router)
app.include_router(review_router)

@app.get("/")
def root():
    return {"message": "ResearchOS backend running"}