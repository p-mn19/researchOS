import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import fitz
from bson import ObjectId
from fastapi import HTTPException

from app.db import papers_collection


def _get_object_id(paper_id: str) -> ObjectId:
    paper_id = str(paper_id or "").strip()

    if not ObjectId.is_valid(paper_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid paper ID: {paper_id!r}",
        )

    return ObjectId(paper_id)


def clean_pdf_text(text: str) -> str:
    if not text:
        return ""

    # Join words broken across PDF line breaks:
    # "meth-\nodology" -> "methodology"
    text = re.sub(r"([A-Za-z])-\s*\n\s*([A-Za-z])", r"\1\2", text)

    # Remove URLs and DOI links.
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"doi:\s*\S+", " ", text, flags=re.IGNORECASE)

    # Remove common DOI and IEEE license fragments.
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

    # Remove bracket-only numeric citations such as [1], [12], [3, 5].
    text = re.sub(
        r"\[\s*\d+(?:\s*[,;-]\s*\d+)*\s*\]",
        " ",
        text,
    )

    # Remove long isolated page-number sequences.
    text = re.sub(
        r"(?:\b\d{1,3}\b[\s]*){8,}",
        " ",
        text,
    )

    # Replace repeated whitespace and line breaks.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _extract_year(text: str) -> Optional[int]:
    first_part = text[:6000]

    matches = re.findall(
        r"\b(19\d{2}|20\d{2})\b",
        first_part,
    )

    current_year = datetime.utcnow().year

    for value in matches:
        year = int(value)

        if 1900 <= year <= current_year + 1:
            return year

    return None


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _extract_title_from_text(
    text: str,
    fallback_title: str,
) -> str:
    lines = [
        _clean_line(line)
        for line in text[:5000].splitlines()
        if _clean_line(line)
    ]

    ignored_lines = {
        "abstract",
        "introduction",
        "keywords",
        "contents",
    }

    for line in lines[:30]:
        lower_line = line.lower()

        if lower_line in ignored_lines:
            continue

        if len(line) < 12:
            continue

        if re.fullmatch(r"\d{4}", line):
            continue

        if "@" in line:
            continue

        return line[:500]

    return fallback_title


def parse_pdf_text(paper_id: str):
    object_id = _get_object_id(paper_id)

    paper = papers_collection.find_one(
        {"_id": object_id}
    )

    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Paper not found",
        )

    filepath = paper.get("filepath")

    if not filepath or not Path(filepath).exists():
        raise HTTPException(
            status_code=404,
            detail="PDF file not found on disk",
        )

    try:
        document = fitz.open(filepath)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not open PDF: {str(exc)}",
        ) from exc

    pages = []
    raw_pages = []

    try:
        for index, page in enumerate(document):
            raw_text = page.get_text("text") or ""
            cleaned_text = clean_pdf_text(raw_text)

            pages.append(
                {
                    "page_number": index + 1,
                    "text": cleaned_text,
                }
            )

            raw_pages.append(cleaned_text)

    finally:
        document.close()

    combined_text = clean_pdf_text(
        "\n".join(raw_pages)
    )

    fallback_title = (
        paper.get("title")
        or Path(
            paper.get("filename", "paper.pdf")
        ).stem.replace("_", " ")
    )

    extracted_title = _extract_title_from_text(
        combined_text,
        fallback_title,
    )

    extracted_year = _extract_year(combined_text)

    update_data = {
        "raw_text": combined_text,
        "pages": pages,
        "title": extracted_title,
        "status": "parsed",
        "parsed_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    if extracted_year is not None:
        update_data["year"] = extracted_year

    papers_collection.update_one(
        {"_id": object_id},
        {"$set": update_data},
    )

    return {
        "paper_id": paper_id,
        "title": extracted_title,
        "year": extracted_year,
        "pages_count": len(pages),
        "characters": len(combined_text),
        "status": "parsed",
    }