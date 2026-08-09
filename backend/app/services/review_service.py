from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import HTTPException

from app.db import papers_collection, extractions_collection


def _text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(str(item) for item in value)

    return str(value).strip()


def _score(value: int) -> str:
    return f"{value}/10"


def _find_paper(paper_id: str) -> Optional[dict]:
    paper_id = str(paper_id or "").strip()

    if not paper_id:
        return None

    # Normal MongoDB ObjectId
    if ObjectId.is_valid(paper_id):
        paper = papers_collection.find_one(
            {"_id": ObjectId(paper_id)}
        )

        if paper:
            return paper

    # Numeric MongoDB _id, for example _id: 1
    if paper_id.isdigit():
        numeric_id = int(paper_id)

        paper = papers_collection.find_one(
            {"_id": numeric_id}
        )

        if paper:
            return paper

        # Legacy documents may store the ID in a normal `id` field
        paper = papers_collection.find_one(
            {"id": paper_id}
        )

        if paper:
            return paper

    return None


def _find_extraction(paper_id: str, paper: dict) -> dict:
    extraction = extractions_collection.find_one(
        {
            "$or": [
                {"paper_id": paper_id},
                {"paper_id": str(paper.get("_id"))},
            ]
        }
    )

    return extraction or {}


def generate_review(paper_id: str) -> Dict[str, Any]:
    paper_id = str(paper_id or "").strip()

    if not paper_id:
        raise HTTPException(
            status_code=400,
            detail="Paper ID is required",
        )

    paper = _find_paper(paper_id)

    if not paper:
        raise HTTPException(
            status_code=404,
            detail=f"Paper not found for ID: {paper_id}",
        )

    extraction = _find_extraction(paper_id, paper)

    title = (
        paper.get("title")
        or paper.get("filename")
        or "Untitled paper"
    )

    abstract = _text(paper.get("abstract"))

    methodology = _text(
        extraction.get("methodology")
        or paper.get("methodology")
    )

    dataset = _text(
        extraction.get("dataset")
        or paper.get("dataset")
    )

    metric = _text(
        extraction.get("evaluation_metric")
        or extraction.get("metrics")
        or paper.get("evaluation_metric")
    )

    limitations = _text(
        extraction.get("limitations")
        or paper.get("limitations")
    )

    future_work = _text(
        extraction.get("future_work")
        or paper.get("future_work")
    )

    clarity_score = 8 if abstract else 5
    methodology_score = 8 if methodology else 4
    dataset_score = 8 if dataset else 4
    metric_score = 8 if metric else 4
    limitation_score = 8 if limitations else 4

    clarity_concern = (
        "None" if clarity_score >= 8 else "Major"
    )

    if (
        methodology_score >= 8
        and dataset_score >= 8
        and metric_score >= 8
    ):
        methodology_concern = "None"
    elif methodology_score >= 6:
        methodology_concern = "Moderate"
    else:
        methodology_concern = "Major"

    claims_concern = "Moderate" if limitations else "Critical"

    dimensions = [
        {
            "id": "clarity",
            "title": "Problem Clarity & Literature Coverage",
            "score": _score(clarity_score),
            "concern": clarity_concern,
            "evidence": (
                "The paper contains an abstract, which provides an "
                "initial description of the research problem and "
                "contribution."
                if abstract
                else
                "No abstract was available in the stored metadata, "
                "so the problem statement and contribution cannot "
                "be fully verified."
            ),
            "suggestion": (
                "Add a concise problem statement and a comparison "
                "table showing how the paper differs from previous work."
            ),
        },
        {
            "id": "novelty",
            "title": "Novelty Heuristic",
            "score": _score(7 if methodology else 5),
            "concern": "Moderate",
            "evidence": (
                "Novelty cannot be treated as a definitive fact by "
                "this simulator. This assessment is based on the "
                "available paper metadata and extracted methodology."
            ),
            "suggestion": (
                "Clearly identify the technical difference from the "
                "strongest existing baselines and related papers."
            ),
        },
        {
            "id": "methodology",
            "title": "Method Justification & Completeness",
            "score": _score(
                min(
                    methodology_score,
                    dataset_score,
                    metric_score,
                )
            ),
            "concern": methodology_concern,
            "evidence": (
                f"Methodology: {methodology or 'not available'}. "
                f"Dataset: {dataset or 'not available'}. "
                f"Evaluation metric: {metric or 'not available'}."
            ),
            "suggestion": (
                "Add complete dataset details, baseline comparisons, "
                "evaluation metrics, and reproducibility information."
            ),
        },
        {
            "id": "claims",
            "title": "Unsupported Claims & Limitations",
            "score": _score(limitation_score),
            "concern": claims_concern,
            "evidence": (
                f"Reported limitations: {limitations}"
                if limitations
                else
                "No explicit limitations were found in the extracted "
                "paper information."
            ),
            "suggestion": (
                "Explicitly state the scope of the experiments, avoid "
                "absolute claims, and document limitations and future work."
            ),
        },
    ]

    average_score = sum(
        int(item["score"].split("/")[0])
        for item in dimensions
    ) / len(dimensions)

    if average_score >= 8:
        overall_label = "Strong Accept"
    elif average_score >= 7:
        overall_label = "Weak Accept"
    elif average_score >= 5:
        overall_label = "Borderline"
    else:
        overall_label = "Weak Reject"

    summary = (
        f"The simulated review of '{title}' found an average rubric "
        f"score of {average_score:.1f}/10. The report is based on the "
        "metadata and structured fields currently available in "
        "ResearchOS. It should be treated as decision support rather "
        "than a real peer-review decision."
    )

    return {
        "paperId": paper_id,
        "paperTitle": title,
        "overallScore": (
            f"{overall_label} ({average_score:.1f}/10)"
        ),
        "summary": summary,
        "dimensions": dimensions,
    }