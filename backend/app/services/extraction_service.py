from bson import ObjectId
from datetime import datetime
from app.db import papers_collection, extractions_collection

def naive_extract_section(text: str, keyword: str, window: int = 600):
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        return ""
    return text[idx: idx + window]

def extract_fields_for_paper(paper_id: str):
    paper = papers_collection.find_one({"_id": ObjectId(paper_id)})
    if not paper or "raw_text" not in paper:
        raise ValueError("Paper not parsed")

    text = paper["raw_text"]

    extraction = {
        "paper_id": paper_id,
        "objective": naive_extract_section(text, "objective"),
        "methodology": naive_extract_section(text, "method"),
        "dataset": naive_extract_section(text, "dataset"),
        "evaluation_metric": naive_extract_section(text, "accuracy"),
        "limitations": naive_extract_section(text, "limitation"),
        "future_work": naive_extract_section(text, "future work"),
        "created_at": datetime.utcnow(),
    }

    extractions_collection.update_one(
        {"paper_id": paper_id},
        {"$set": extraction},
        upsert=True
    )

    papers_collection.update_one(
        {"_id": ObjectId(paper_id)},
        {"$set": {"status": "extracted", "extracted_at": datetime.utcnow()}}
    )

    return extraction