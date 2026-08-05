from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="ResearchOS API")

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

class SearchRequest(BaseModel):
    query: str

class CompareRequest(BaseModel):
    paper_ids: list[str]

papers = [
    {
        "id": "1",
        "title": "ResearchOS Demo Paper",
        "filename": "demo-paper.pdf",
        "authors": ["Vaishnavi Balodhi"],
        "year": 2026,
        "abstract": "Demo abstract for frontend testing.",
        "status": "uploaded",
    }
]

@app.get("/")
def root():
    return {"message": "ResearchOS API is running"}

@app.get("/papers")
def get_papers():
    return papers

@app.get("/papers/{paper_id}")
def get_paper(paper_id: str):
    for paper in papers:
        if paper["id"] == paper_id:
            return paper
    return {
        "id": paper_id,
        "title": "Untitled paper",
        "filename": "unknown.pdf",
        "status": "uploaded",
    }

@app.get("/papers/{paper_id}/extraction")
def get_extraction(paper_id: str):
    return {
        "objective": "Assist researchers with literature review and analysis.",
        "methodology": "RAG + semantic search + structured extraction.",
        "dataset": "Uploaded research corpus",
        "evaluation_metric": "Accuracy and relevance",
        "limitations": "Prototype stage",
        "future_work": "Add reviewer simulation and LaTeX export",
    }

@app.post("/papers/upload")
async def upload_paper(file: UploadFile = File(...)):
    return {
        "message": f"Uploaded {file.filename}",
        "filename": file.filename,
    }

@app.post("/papers/{paper_id}/parse")
def parse_paper(paper_id: str):
    return {"message": f"Paper {paper_id} parsed successfully"}

@app.post("/papers/{paper_id}/extract")
def extract_paper(paper_id: str):
    return {"message": f"Paper {paper_id} extracted successfully"}

@app.post("/papers/{paper_id}/search")
def search_paper(paper_id: str, body: SearchRequest):
    return [
        {
            "id": "chunk-1",
            "section_title": "Methodology",
            "page": 3,
            "text": f"Result for query: {body.query}",
            "score": 0.93,
        }
    ]

@app.post("/compare")
def compare(body: CompareRequest):
    return [
        {
            "field": "Methodology",
            "values": {pid: "RAG-based pipeline" for pid in body.paper_ids},
        },
        {
            "field": "Dataset",
            "values": {pid: "Uploaded PDF corpus" for pid in body.paper_ids},
        },
        {
            "field": "Limitation",
            "values": {pid: "Prototype stage" for pid in body.paper_ids},
        },
    ]