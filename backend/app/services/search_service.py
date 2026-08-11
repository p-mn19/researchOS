import re
from typing import Any, Dict, List, Optional, Set

from bson import ObjectId

from app.db import chunks_collection, papers_collection


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "used",
    "was",
    "what",
    "which",
    "with",
}


def clean_display_text(text: str) -> str:
    if not text:
        return ""

    text = re.sub(
        r"([A-Za-z])-\s*\n\s*([A-Za-z])",
        r"\1\2",
        text,
    )

    text = re.sub(
        r"https?://\S+",
        " ",
        text,
    )

    text = re.sub(
        r"doi:\s*\S+",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\b978[-\d]+(?:/\$\d+(?:\.\d+)?)?\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\$\d+(?:\.\d+)?",
        " ",
        text,
    )

    text = re.sub(
        r"©\s*\d{4}[^.\n]*",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\[\s*\d+(?:\s*[,;-]\s*\d+)*\s*\]",
        " ",
        text,
    )

    text = re.sub(
        r"(?:\b\d{1,3}\b[\s]*){8,}",
        " ",
        text,
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _tokens(value: str) -> Set[str]:
    words = re.findall(
        r"[a-zA-Z0-9]+",
        value.lower(),
    )

    return {
        word
        for word in words
        if word not in STOP_WORDS and len(word) > 1
    }


def _stringify(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(
            _stringify(item)
            for item in value
        )

    if isinstance(value, dict):
        return " ".join(
            _stringify(item)
            for item in value.values()
        )

    return str(value)


def _first_value(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value

    return None


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None

        return int(value)

    except (TypeError, ValueError):
        return None


def _score(query: str, text: str) -> float:
    query_tokens = _tokens(query)
    text_tokens = _tokens(text)

    if not query_tokens or not text_tokens:
        return 0.0

    matched_tokens = query_tokens.intersection(text_tokens)

    if not matched_tokens:
        return 0.0

    score = len(matched_tokens) / len(query_tokens)

    normalized_query = " ".join(
        query.lower().split()
    )

    normalized_text = " ".join(
        text.lower().split()
    )

    if normalized_query in normalized_text:
        score += 0.25

    return min(score, 1.0)


def _create_snippet(
    text: str,
    query: str,
    max_length: int = 420,
) -> str:
    text = clean_display_text(text)

    if not text:
        return ""

    if len(text) <= max_length:
        return text

    query_tokens = list(_tokens(query))
    lower_text = text.lower()

    positions = []

    for token in query_tokens:
        position = lower_text.find(token.lower())

        if position >= 0:
            positions.append(position)

    if not positions:
        return f"{text[:max_length].rstrip()}..."

    match_position = min(positions)

    context_before = 120
    start = max(0, match_position - context_before)
    end = min(len(text), start + max_length)

    snippet = text[start:end].strip()

    if start > 0:
        snippet = f"...{snippet}"

    if end < len(text):
        snippet = f"{snippet}..."

    return snippet


def _normalise_paper_ids(
    paper_ids: Optional[List[str]],
) -> Optional[List[str]]:
    if not paper_ids:
        return None

    normalized = []

    for paper_id in paper_ids:
        value = str(paper_id or "").strip()

        if value:
            normalized.append(value)

    return normalized or None


def _paper_filter(
    paper_ids: Optional[List[str]],
) -> Optional[Dict[str, Any]]:
    normalized_ids = _normalise_paper_ids(paper_ids)

    if not normalized_ids:
        return None

    object_ids = [
        ObjectId(paper_id)
        for paper_id in normalized_ids
        if ObjectId.is_valid(paper_id)
    ]

    values: List[Any] = list(normalized_ids)
    values.extend(object_ids)

    return {"$in": values}


def _paper_lookup() -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}

    for paper in papers_collection.find():
        paper_id = str(paper["_id"])
        lookup[paper_id] = paper

        if paper.get("id") is not None:
            lookup[str(paper["id"])] = paper

    return lookup


def _get_chunk_paper_id(
    chunk: Dict[str, Any],
) -> str:
    raw_paper_id = _first_value(
        chunk.get("paper_id"),
        chunk.get("paperId"),
    )

    if raw_paper_id is None:
        return ""

    return str(raw_paper_id)


def _search_chunks(
    query: str,
    paper_ids: Optional[List[str]],
    top_k: int,
) -> List[Dict[str, Any]]:
    mongo_query: Dict[str, Any] = {}

    paper_filter = _paper_filter(paper_ids)

    if paper_filter:
        mongo_query["paper_id"] = paper_filter

    chunks = list(
        chunks_collection.find(mongo_query)
    )

    papers = _paper_lookup()
    results: List[Dict[str, Any]] = []

    for index, chunk in enumerate(chunks):
        raw_text = _first_value(
            chunk.get("text"),
            chunk.get("chunk_text"),
            chunk.get("content"),
        )

        text = _stringify(raw_text)

        if not text.strip():
            continue

        score = _score(query, text)

        if score <= 0:
            continue

        paper_id = _get_chunk_paper_id(chunk)
        paper = papers.get(paper_id, {})

        page = _to_int(
            _first_value(
                chunk.get("page"),
                chunk.get("page_number"),
                chunk.get("page_no"),
                chunk.get("pageno"),
                chunk.get("pageNum"),
            )
        )

        section_title = _first_value(
            chunk.get("section_title"),
            chunk.get("section"),
            chunk.get("section_name"),
        )

        raw_chunk_id = chunk.get("_id")

        result_id = (
            str(raw_chunk_id)
            if raw_chunk_id is not None
            else f"chunk-{index}"
        )

        results.append(
            {
                "id": result_id,
                "paper_id": paper_id,
                "paper_title": (
                    paper.get("title")
                    or paper.get("filename")
                    or "Untitled paper"
                ),
                "filename": paper.get("filename"),
                "section_title": section_title,
                "page": page,
                "text": _create_snippet(text, query),
                "score": round(score, 4),
            }
        )

    results.sort(
        key=lambda result: result["score"],
        reverse=True,
    )

    return results[:top_k]


def _search_papers(
    query: str,
    paper_ids: Optional[List[str]],
    top_k: int,
) -> List[Dict[str, Any]]:
    mongo_query: Dict[str, Any] = {}

    paper_filter = _paper_filter(paper_ids)

    if paper_filter:
        mongo_query["_id"] = paper_filter

    papers = list(
        papers_collection.find(mongo_query)
    )

    results: List[Dict[str, Any]] = []

    searchable_fields = [
        "title",
        "abstract",
        "raw_text",
        "methodology",
        "dataset",
        "limitations",
        "future_work",
    ]

    for paper in papers:
        parts = []

        for field in searchable_fields:
            value = paper.get(field)

            if value:
                parts.append(_stringify(value))

        full_text = clean_display_text(
            " ".join(parts)
        )

        score = _score(query, full_text)

        if score <= 0:
            continue

        paper_id = str(paper["_id"])

        results.append(
            {
                "id": paper_id,
                "paper_id": paper_id,
                "paper_title": (
                    paper.get("title")
                    or paper.get("filename")
                    or "Untitled paper"
                ),
                "filename": paper.get("filename"),
                "section_title": None,
                "page": None,
                "text": _create_snippet(
                    full_text,
                    query,
                ),
                "score": round(score, 4),
            }
        )

    results.sort(
        key=lambda result: result["score"],
        reverse=True,
    )

    return results[:top_k]


def semantic_search(
    query: str,
    paper_ids: Optional[List[str]] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    query = str(query or "").strip()

    if not query:
        return []

    top_k = max(
        1,
        min(int(top_k), 20),
    )

    chunk_results = _search_chunks(
        query=query,
        paper_ids=paper_ids,
        top_k=top_k,
    )

    if chunk_results:
        return chunk_results

    return _search_papers(
        query=query,
        paper_ids=paper_ids,
        top_k=top_k,
    )