from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="ResearchOS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
        "title": "The Kepler end-to-end data pipeline from photons to planets",
        "filename": "The_Kepler_end-to-end_data_pipeline_from_photons_to_planets.pdf",
        "authors": ["Research Team A"],
        "year": 2024,
        "abstract": "A paper on automated exoplanet detection workflows.",
        "status": "uploaded",
        "methodology": "End-to-end pipeline with data preprocessing and model inference.",
        "dataset": "Kepler telescope observations",
        "limitations": "Limited generalization beyond Kepler-like data.",
    },
    {
        "id": "2",
        "title": "AstroFusion: A GAN-Augmented Approach for Exoplanet Detection",
        "filename": "AstroFusion_A_GAN-Augmented_Approach_for_Exoplanet_Detection.pdf",
        "authors": ["Research Team B"],
        "year": 2023,
        "abstract": "GAN-augmented exoplanet detection using synthetic examples.",
        "status": "uploaded",
        "methodology": "GAN augmentation with a classification pipeline.",
        "dataset": "Astronomical light-curve data",
        "limitations": "Synthetic data may not fully match real distribution.",
    },
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
    return {"detail": "Not Found"}

@app.get("/papers/{paper_id}/extraction")
def get_extraction(paper_id: str):
    for paper in papers:
        if paper["id"] == paper_id:
            return {
                "objective": paper.get("abstract", ""),
                "methodology": paper.get("methodology", "Not extracted yet"),
                "dataset": paper.get("dataset", "Not extracted yet"),
                "evaluation_metric": "Accuracy / F1 / AUROC",
                "limitations": paper.get("limitations", "Not extracted yet"),
                "future_work": "Expand to broader datasets and stronger validation.",
            }
    return {"detail": "Not Found"}

@app.post("/papers/upload")
async def upload_paper(file: UploadFile = File(...)):
    paper_id = str(len(papers) + 1)
    paper = {
        "id": paper_id,
        "title": file.filename.rsplit(".", 1)[0],
        "filename": file.filename,
        "authors": [],
        "year": 2026,
        "abstract": "",
        "status": "uploaded",
        "methodology": "Not extracted yet",
        "dataset": "Not extracted yet",
        "limitations": "Not extracted yet",
    }
    papers.append(paper)
    return {"message": "Upload successful", "paper": paper}

@app.post("/papers/{paper_id}/parse")
def parse_paper(paper_id: str):
    for paper in papers:
        if paper["id"] == paper_id:
            paper["status"] = "parsed"
            paper["abstract"] = f"Parsed abstract for {paper['title']}"
            return {"message": f"Paper {paper_id} parsed successfully", "paper": paper}
    return {"detail": "Not Found"}

@app.post("/papers/{paper_id}/extract")
def extract_paper(paper_id: str):
    for paper in papers:
        if paper["id"] == paper_id:
            paper["status"] = "extracted"
            paper["methodology"] = f"Methodology extracted from {paper['title']}"
            paper["dataset"] = f"Dataset extracted from {paper['title']}"
            paper["limitations"] = f"Limitations extracted from {paper['title']}"
            return {"message": f"Paper {paper_id} extracted successfully", "paper": paper}
    return {"detail": "Not Found"}

@app.post("/papers/{paper_id}/search")
def search_paper(paper_id: str, body: SearchRequest):
    for paper in papers:
        if paper["id"] == paper_id:
            return [
                {
                    "id": f"{paper_id}-chunk-1",
                    "section_title": "Introduction",
                    "page": 1,
                    "text": f"Search result for '{body.query}' in {paper['title']}.",
                    "score": 0.92,
                },
                {
                    "id": f"{paper_id}-chunk-2",
                    "section_title": "Methodology",
                    "page": 3,
                    "text": f"Relevant section discussing the approach in {paper['title']}.",
                    "score": 0.87,
                },
            ]
    return {"detail": "Not Found"}

@app.post("/compare")
def compare(body: CompareRequest):
    selected = [p for p in papers if p["id"] in body.paper_ids]
    return [
        {
            "field": "Year",
            "values": {p["id"]: str(p.get("year", "—")) for p in selected},
        },
        {
            "field": "Methodology",
            "values": {p["id"]: p.get("methodology", "Not extracted yet") for p in selected},
        },
        {
            "field": "Dataset",
            "values": {p["id"]: p.get("dataset", "Not extracted yet") for p in selected},
        },
        {
            "field": "Limitation",
            "values": {p["id"]: p.get("limitations", "Not extracted yet") for p in selected},
        },
    ]