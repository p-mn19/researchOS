from typing import Any, Dict, List


from bson import ObjectId


from app.db import extractions_collection, papers_collection


COMPARE_FIELDS = [
    "objective",
    "methodology",
    "dataset",
    "evaluation_metric",
    "limitations",
    "future_work",
    "research_gap",
    "findings",
    "keywords",
]


def _text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(str(item) for item in value)

    return str(value).strip()


def _paper_query_ids(paper_ids: List[str]) -> List[Any]:
    values = []

    for paper_id in paper_ids:
        value = str(paper_id).strip()

        if ObjectId.is_valid(value):
            values.append(ObjectId(value))
        else:
            values.append(value)

    return values


def compare_papers(paper_ids: List[str]) -> Dict[str, Any]:
    paper_ids = [
        str(paper_id).strip()
        for paper_id in paper_ids
        if str(paper_id).strip()
    ]

    if len(paper_ids) < 2:
        raise ValueError("At least two papers are required")

    if len(paper_ids) > 4:
        raise ValueError("A maximum of four papers can be compared")

    query_ids = _paper_query_ids(paper_ids)

    paper_documents = list(
        papers_collection.find(
            {
                "_id": {
                    "$in": query_ids,
                }
            }
        )
    )

    paper_map: Dict[str, str] = {}

    for paper in paper_documents:
        paper_id = str(paper["_id"])

        paper_map[paper_id] = (
            paper.get("title")
            or paper.get("filename")
            or "Untitled paper"
        )

    extraction_documents = list(
        extractions_collection.find(
            {
                "$or": [
                    {"paper_id": {"$in": paper_ids}},
                    {"paper_id": {"$in": query_ids}},
                ]
            }
        )
    )

    extraction_map: Dict[str, Dict[str, Any]] = {}

    for extraction in extraction_documents:
        raw_paper_id = extraction.get("paper_id")

        if raw_paper_id is None:
            continue

        extraction_map[str(raw_paper_id)] = extraction

    rows = []

    for field in COMPARE_FIELDS:
        row_values: Dict[str, str] = {}

        for paper_id in paper_ids:
            extraction = extraction_map.get(paper_id, {})
            value = extraction.get(field, "")

            if not value:
                matching_document = next(
                    (
                        paper
                        for paper in paper_documents
                        if str(paper["_id"]) == paper_id
                    ),
                    {},
                )

                value = matching_document.get(field, "")

            row_values[paper_id] = _text(value) or "—"

        rows.append(
            {
                "field": field.replace("_", " ").title(),
                "values": row_values,
            }
        )

    return {
        "rows": rows,
        "paper_map": paper_map,
    }