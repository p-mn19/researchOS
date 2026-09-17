from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb

from app.config import VECTOR_DIR


COLLECTION_NAME = "research_papers"


VECTOR_PATH = Path(VECTOR_DIR)
VECTOR_PATH.mkdir(
    parents=True,
    exist_ok=True,
)


chroma_client = chromadb.PersistentClient(
    path=str(VECTOR_PATH),
)

collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={
        "description": "ResearchOS paper chunks",
    },
)


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


def _safe_page(value: Any) -> str:
    if value is None or value == "":
        return ""

    return str(value)


def _chunk_id(
    paper_id: str,
    chunk: Dict[str, Any],
    index: int,
) -> str:
    value = _first_value(
        chunk.get("id"),
        chunk.get("chunk_id"),
        chunk.get("_id"),
    )

    if value is None:
        return f"{paper_id}-chunk-{index}"

    return str(value)


def _metadata(
    paper_id: str,
    chunk: Dict[str, Any],
) -> Dict[str, str]:
    return {
        "paper_id": str(paper_id),
        "page": _safe_page(
            _first_value(
                chunk.get("page"),
                chunk.get("page_number"),
                chunk.get("page_no"),
            )
        ),
        "section_title": _stringify(
            _first_value(
                chunk.get("section_title"),
                chunk.get("section"),
                chunk.get("section_name"),
            )
        ),
        "paper_title": _stringify(
            _first_value(
                chunk.get("paper_title"),
                chunk.get("title"),
                "",
            )
        ),
    }


def index_paper_chunks(
    paper_id: str,
    chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    paper_id = str(paper_id or "").strip()

    if not paper_id:
        raise ValueError("paper_id is required")

    if not chunks:
        return {
            "paper_id": paper_id,
            "indexed": 0,
        }

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict[str, str]] = []

    for index, chunk in enumerate(chunks):
        text = _stringify(
            _first_value(
                chunk.get("text"),
                chunk.get("chunk_text"),
                chunk.get("content"),
            )
        ).strip()

        if not text:
            continue

        ids.append(_chunk_id(paper_id, chunk, index))
        documents.append(text)
        metadatas.append(_metadata(paper_id, chunk))

    if not documents:
        return {
            "paper_id": paper_id,
            "indexed": 0,
        }

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    return {
        "paper_id": paper_id,
        "indexed": len(documents),
    }


def delete_paper_vectors(paper_id: str) -> Dict[str, Any]:
    paper_id = str(paper_id or "").strip()

    if not paper_id:
        raise ValueError("paper_id is required")

    existing = collection.get(
        where={"paper_id": paper_id},
    )

    ids = existing.get("ids") or []

    if ids:
        collection.delete(ids=ids)

    return {
        "paper_id": paper_id,
        "deleted": len(ids),
    }


def search_paper_chunks(
    query: str,
    paper_id: Optional[str] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    query = str(query or "").strip()

    if not query:
        return []

    top_k = max(1, min(int(top_k), 20))

    kwargs: Dict[str, Any] = {
        "query_texts": [query],
        "n_results": top_k,
        "include": [
            "documents",
            "metadatas",
            "distances",
        ],
    }

    if paper_id:
        kwargs["where"] = {
            "paper_id": str(paper_id),
        }

    result = collection.query(**kwargs)

    documents = result.get("documents") or [[]]
    metadatas = result.get("metadatas") or [[]]
    distances = result.get("distances") or [[]]
    ids = result.get("ids") or [[]]

    document_values = documents[0] if documents else []
    metadata_values = metadatas[0] if metadatas else []
    distance_values = distances[0] if distances else []
    id_values = ids[0] if ids else []

    output: List[Dict[str, Any]] = []

    for index, document in enumerate(document_values):
        metadata = (
            metadata_values[index]
            if index < len(metadata_values)
            else {}
        ) or {}

        distance = (
            distance_values[index]
            if index < len(distance_values)
            else None
        )

        chunk_id = (
            id_values[index]
            if index < len(id_values)
            else f"result-{index}"
        )

        score = None

        if distance is not None:
            score = round(
                1 / (1 + float(distance)),
                4,
            )

        output.append(
            {
                "id": str(chunk_id),
                "paper_id": metadata.get("paper_id") or paper_id,
                "paper_title": metadata.get("paper_title"),
                "section_title": metadata.get("section_title"),
                "page": metadata.get("page") or None,
                "text": str(document or ""),
                "score": score,
            }
        )

    return output