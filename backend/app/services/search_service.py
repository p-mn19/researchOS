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


def _stringify(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(_stringify(item) for item in value)

    if isinstance(value, dict):
        return " ".join(_stringify(item) for item in value.values())

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


def clean_display_text(text: str) -> str:
    if not text:
        return ""

    # Join words broken across PDF line breaks.
    text = re.sub(
        r"([A-Za-z])-\s*\n\s*([A-Za-z])",
        r"\1\2",
        text,
    )

    # Remove URLs and DOI strings.
    text = re.sub(r"https?://\S+", " ", text)
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

    # Remove common publisher/license fragments.
    text = re.sub(
        r"\b978[-\d]+(?:/\$\d+(?:\.\d+)?)?\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\$\d+(?:\.\d+)?", " ", text)
    text = re.sub(
        r"©\s*\d{4}[^.\n]*",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # Remove numeric citation markers such as [1] or [2, 5].
    text = re.sub(
        r"\[\s*\d+(?:\s*[,;-]\s*\d+)*\s*\]",
        " ",
        text,
    )

    # Remove PDF control characters and black rectangle artifacts.
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text)
    text = re.sub(r"[■□▪▫▬▲▼◆◇▶◀●○�]+", " ", text)

    # Remove unsupported replacement glyphs while preserving normal text.
    text = re.sub(
        r"[^\x20-\x7E\u00A0-\u024F\u1E00-\u1EFF\n\r\t]",
        " ",
        text,
    )

    text = text.encode("utf-8", "ignore").decode(
        "utf-8",
        "ignore",
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


def _score(query: str, text: str) -> float:
    query_tokens = _tokens(query)
    text_tokens = _tokens(text)

    if not query_tokens or not text_tokens:
        return 0.0

    matched_tokens = query_tokens.intersection(text_tokens)
    score = len(matched_tokens) / len(query_tokens)

    normalized_query = " ".join(query.lower().split())
    normalized_text = " ".join(text.lower().split())

    if normalized_query in normalized_text:
        score += 0.25

    return min(score, 1.0)


def _create_snippet(
    text: str,
    query: str,
    max_length: int = 520,
) -> str:
    text = clean_display_text(text)

    if not text:
        return ""

    if len(text) <= max_length:
        return text

    normalized_text = text.lower()
    positions = []

    for token in _tokens(query):
        position = normalized_text.find(token.lower())

        if position >= 0:
            positions.append(position)

    match_position = min(positions) if positions else 0
    start = max(0, match_position - 130)
    end = min(len(text), start + max_length)

    snippet = text[start:end].strip()

    if start > 0:
        snippet = f"...{snippet}"

    if end < len(text):
        snippet = f"{snippet}..."

    return snippet


def _paper_lookup() -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}

    for paper in papers_collection.find():
        paper_id = str(paper["_id"])
        lookup[paper_id] = paper

        if paper.get("id") is not None:
            lookup[str(paper["id"])] = paper

    return lookup


def _normalise_paper_ids(
    paper_ids: Optional[List[str]],
) -> Optional[List[str]]:
    if not paper_ids:
        return None

    values = []

    for paper_id in paper_ids:
        value = str(paper_id or "").strip()

        if value:
            values.append(value)

    return values or None


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


def _chunk_paper_id(chunk: Dict[str, Any]) -> str:
    value = _first_value(
        chunk.get("paper_id"),
        chunk.get("paperId"),
    )

    return str(value) if value is not None else ""


def _search_chunks(
    query: str,
    paper_ids: Optional[List[str]],
    top_k: int,
) -> List[Dict[str, Any]]:
    mongo_query: Dict[str, Any] = {}
    paper_filter = _paper_filter(paper_ids)

    if paper_filter:
        mongo_query["paper_id"] = paper_filter

    chunks = list(chunks_collection.find(mongo_query))
    papers = _paper_lookup()
    results: List[Dict[str, Any]] = []

    for index, chunk in enumerate(chunks):
        raw_text = _first_value(
            chunk.get("text"),
            chunk.get("chunk_text"),
            chunk.get("content"),
        )

        original_text = _stringify(raw_text)

        if not original_text.strip():
            continue

        score = _score(query, original_text)

        if score <= 0:
            continue

        paper_id = _chunk_paper_id(chunk)
        paper = papers.get(paper_id, {})

        page = _to_int(
            _first_value(
                chunk.get("page"),
                chunk.get("page_number"),
                chunk.get("page_no"),
                chunk.get("pageNum"),
            )
        )

        section_title = _first_value(
            chunk.get("section_title"),
            chunk.get("section"),
            chunk.get("section_name"),
        )

        chunk_id = chunk.get("_id")

        results.append(
            {
                "id": paper_id,
                "paper_id": paper_id,
                "paper_title": (
                    paper.get("title")
                    or paper.get("filename")
                    or "Untitled paper"
                ),
                "filename": paper.get(
                    "filename"
                ),
                "section_title": None,
                "page": None,
                "text": _create_snippet(
                    full_text,
                    query,
                    max_length=1800,
                ),
                "score": round(score, 4),
                "metadata": {
                    "research_gap": paper.get("research_gap"),
                    "limitations": paper.get("limitations"),
                    "methodology": paper.get("methodology"),
                    "findings": paper.get("findings"),
                    "future_work": paper.get("future_work"),
                    "keywords": paper.get("keywords", []),
                },
            }
        )

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results[:top_k]


def _search_selected_paper_text(
    query: str,
    paper_ids: List[str],
    top_k: int,
) -> List[Dict[str, Any]]:
    paper_filter = _paper_filter(paper_ids)

    if not paper_filter:
        return []

    papers = papers_collection.find(
        {"_id": paper_filter}
    )

    results = []

    for paper in papers:
        full_text = clean_display_text(
            _stringify(
                paper.get("raw_text")
                or paper.get("text")
                or ""
            )
        )

        if not full_text:
            continue

        score = _score(
            query,
            full_text,
        )

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
                "filename": paper.get(
                    "filename"
                ),
                "section_title": None,
                "page": None,
                "text": _create_snippet(
                    full_text,
                    query,
                    max_length=1800,
                ),
                "score": round(score, 4),
            }
        )

    results.sort(
        key=lambda item: item["score"],
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

    if paper_ids:
        selected_results = (
            _search_selected_paper_text(
                query=query,
                paper_ids=paper_ids,
                top_k=top_k,
            )
        )

        if selected_results:
            return selected_results

        # If the selected paper has chunks but
        # keyword matching failed, return only
        # that paper's chunks.
        paper_filter = _paper_filter(
            paper_ids
        )

        mongo_query = {}

        if paper_filter:
            mongo_query["paper_id"] = (
                paper_filter
            )

        fallback_chunks = list(
            chunks_collection.find(
                mongo_query
            ).limit(top_k)
        )

        papers = _paper_lookup()
        results = []

        for index, chunk in enumerate(
            fallback_chunks
        ):
            paper_id = _chunk_paper_id(chunk)
            paper = papers.get(
                paper_id,
                {},
            )

            text = _stringify(
                _first_value(
                    chunk.get("text"),
                    chunk.get("chunk_text"),
                    chunk.get("content"),
                )
            )

            if not text.strip():
                continue

            results.append(
                {
                    "id": str(
                        chunk.get("_id")
                    ),
                    "paper_id": paper_id,
                    "paper_title": (
                        paper.get("title")
                        or paper.get("filename")
                        or "Untitled paper"
                    ),
                    "filename": paper.get(
                        "filename"
                    ),
                    "section_title": chunk.get(
                        "section_title"
                    ),
                    "page": _to_int(
                        _first_value(
                            chunk.get("page"),
                            chunk.get("page_number"),
                        )
                    ),
                    "text": _create_snippet(
                        text,
                        query,
                        max_length=1800,
                    ),
                    "score": 0.01,
                }
            )

        return results[:top_k]

    return _search_papers(
        query=query,
        paper_ids=None,
        top_k=top_k,
    )