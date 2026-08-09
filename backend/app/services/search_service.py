from typing import Any, Dict, List, Optional
from bson import ObjectId
from app.db import papers_collection

SEARCH_FIELDS = [
    "title",
    "abstract",
    "methodology",
    "dataset",
    "limitations",
    "future_work",
    "extracted_text",
    "content",
]


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join([_stringify(v) for v in value])
    return str(value)


def _paper_to_text(paper: Dict[str, Any]) -> str:
    parts = []
    for field in SEARCH_FIELDS:
        val = paper.get(field)
        if val:
            parts.append(_stringify(val))
    return " ".join(parts).lower()


def _match_score(query: str, text: str) -> float:
    if not text:
        return 0.0
    q_terms = [t for t in query.lower().split() if t.strip()]
    if not q_terms:
        return 0.0

    score = 0.0
    for term in q_terms:
        if term in text:
            score += 1.0
    return score / len(q_terms)


def semantic_search(query: str, paper_ids: Optional[List[str]] = None, top_k: int = 5):
    if not query or not query.strip():
        return []

    mongo_query: Dict[str, Any] = {}
    if paper_ids:
        object_ids = []
        for pid in paper_ids:
            if ObjectId.is_valid(pid):
                object_ids.append(ObjectId(pid))
        if object_ids:
            mongo_query["_id"] = {"$in": object_ids}

    papers = list(papers_collection.find(mongo_query))
    results = []

    for paper in papers:
        text = _paper_to_text(paper)
        score = _match_score(query, text)

        if score <= 0:
            continue

        paper_id = str(paper["_id"])
        results.append(
            {
                "paper_id": paper_id,
                "paper_title": paper.get("title") or paper.get("filename") or "Untitled paper",
                "filename": paper.get("filename"),
                "section_title": paper.get("section_title"),
                "page": paper.get("page"),
                "text": paper.get("abstract")
                or paper.get("methodology")
                or paper.get("dataset")
                or paper.get("limitations")
                or paper.get("future_work")
                or paper.get("extracted_text")
                or paper.get("content")
                or "",
                "score": round(score, 4),
            }
        )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]