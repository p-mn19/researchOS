from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from groq import Groq

from app.config import settings


client = None

if settings.GROQ_API_KEY.strip():
    client = Groq(
        api_key=settings.GROQ_API_KEY.strip(),
        base_url="https://api.groq.com",
        timeout=60.0,
        max_retries=2,
    )

SYSTEM_PROMPT = """
You are ResearchOS, an academic research assistant.

Answer only from the supplied paper passages.
Do not invent facts, datasets, methods, results, citations, or numbers.
If the passages do not contain the answer, say that clearly.

Return clean Markdown:
- Begin with a direct answer.
- Use headings when helpful.
- Use bullet points for multiple items.
- Use tables only for genuinely tabular information.
- Use complete sentences.
- Do not output HTML tags.
- Do not output <br>, <p>, or <b>.
- Do not wrap the response in a code block.
- Cite supplied passages as [Source 1], [Source 2], etc.
""".strip()


def _text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(
            _text(item)
            for item in value
        )

    if isinstance(value, dict):
        return " ".join(
            _text(item)
            for item in value.values()
        )

    return str(value)


def build_context(
    chunks: List[Dict[str, Any]],
) -> str:
    blocks = []

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        chunk_text = _text(
            chunk.get("text")
            or chunk.get("chunk_text")
            or chunk.get("content")
        ).strip()

        if not chunk_text:
            continue

        page = (
            chunk.get("page")
            or chunk.get("page_number")
        )

        location = (
            f", page {page}"
            if page
            else ""
        )

        blocks.append(
            "\n".join(
                [
                    f"[Source {index}{location}]",
                    chunk_text,
                ]
            )
        )

    return "\n\n".join(blocks)


def _source_metadata(
    chunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    return [
        {
            "source_number": index,
            "paper_title": (
                chunk.get("paper_title")
                or chunk.get("title")
            ),
            "page": (
                chunk.get("page")
                or chunk.get("page_number")
            ),
            "section_title": (
                chunk.get("section_title")
                or chunk.get("section")
            ),
            "score": chunk.get("score"),
        }
        for index, chunk in enumerate(
            chunks,
            start=1,
        )
    ]


def _clean_answer(answer: str) -> str:
    return (
        answer.replace("<br>", "\n")
        .replace("<br/>", "\n")
        .replace("<br />", "\n")
        .strip()
    )


def generate_grounded_answer(
    question: str,
    chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    question = question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty",
        )

    if not chunks:
        return {
            "answer": (
                "I could not find relevant passages "
                "in this paper for that question."
            ),
            "sources": [],
            "model": settings.GROQ_MODEL,
        }

    if client is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "GROQ_API_KEY is missing. Add it "
                "to backend/.env and restart the "
                "backend."
            ),
        )

    context = build_context(chunks)

    prompt = f"""
Question:
{question}

Paper passages:
{context}

Write a detailed answer in clean Markdown.
Use only the supplied passages.
""".strip()

    try:
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            temperature=0.2,
            max_tokens=2200,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "AI provider request failed: "
                f"{str(exc)}"
            ),
        ) from exc

    answer = ""

    if completion.choices:
        answer = (
            completion.choices[0]
            .message.content
            or ""
        )

    return {
        "answer": _clean_answer(answer),
        "sources": _source_metadata(chunks),
        "model": settings.GROQ_MODEL,
    }

def build_corpus_context(
    papers: List[Dict[str, Any]],
    focus_fields: Optional[List[str]] = None,
) -> str:
    """
    Build a text context from a list of paper documents,
    optionally focusing on specific fields such as
    ['research_gap', 'limitations', 'methodology'].
    Useful for Module 8 ideation and Module 9 drafting.
    """
    if focus_fields is None:
        focus_fields = [
            "title",
            "abstract",
            "research_gap",
            "limitations",
            "methodology",
            "findings",
            "future_work",
        ]

    blocks = []

    for i, paper in enumerate(papers, start=1):
        title = paper.get("title") or paper.get("filename") or f"Paper {i}"
        parts = [f"[Paper {i}] {title}"]

        for field in focus_fields:
            value = paper.get(field)
            if value:
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                if value and str(value).strip():
                    parts.append(f"{field.upper()}: {value}")

        blocks.append("\n".join(parts))

    return "\n\n".join(blocks)