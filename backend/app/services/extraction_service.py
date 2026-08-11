from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException

from app.db import extractions_collection, papers_collection


def _get_object_id(paper_id: str) -> ObjectId:
    paper_id = str(paper_id or "").strip()

    if not ObjectId.is_valid(paper_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid paper ID: {paper_id!r}",
        )

    return ObjectId(paper_id)


def naive_extract_section(
    text: str,
    keywords: list[str],
    window: int = 900,
) -> str:
    if not text:
        return ""

    lower_text = text.lower()

    for keyword in keywords:
        index = lower_text.find(keyword.lower())

        if index != -1:
            extracted = text[index : index + window]
            return " ".join(extracted.split())

    return ""


def extract_fields_for_paper(paper_id: str):
    object_id = _get_object_id(paper_id)

    paper = papers_collection.find_one({"_id": object_id})

    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Paper not found",
        )

    raw_text = paper.get("raw_text", "")

    if not raw_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Paper must be parsed before extraction",
        )

    extraction = {
        "paper_id": paper_id,
        "objective": naive_extract_section(
            raw_text,
            ["objective", "aim", "research problem"],
        ),
        "methodology": naive_extract_section(
            raw_text,
            ["methodology", "method", "proposed method"],
        ),
        "dataset": naive_extract_section(
            raw_text,
            ["dataset", "data set", "data used", "experimental data"],
        ),
        "evaluation_metric": naive_extract_section(
            raw_text,
            [
                "evaluation metric",
                "evaluation metrics",
                "accuracy",
                "precision",
                "recall",
                "f1-score",
            ],
        ),
        "limitations": naive_extract_section(
            raw_text,
            ["limitations", "limitation", "drawbacks"],
        ),
        "future_work": naive_extract_section(
            raw_text,
            ["future work", "future scope", "next steps"],
        ),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    extractions_collection.update_one(
        {"paper_id": paper_id},
        {"$set": extraction},
        upsert=True,
    )

    papers_collection.update_one(
        {"_id": object_id},
        {
            "$set": {
                "status": "extracted",
                "extracted_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return extraction