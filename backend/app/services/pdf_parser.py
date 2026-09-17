import re
from datetime import datetime
from pathlib import Path

import pymupdf
from bson import ObjectId
from fastapi import HTTPException

from app.db import papers_collection


YEAR_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\b"
)


def clean_pdf_text(text: str) -> str:
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
        r"[■□▪▫▬▲▼◆◇▶◀●○�]+",
        " ",
        text,
    )

    # Preserve newline characters because the
    # extraction service uses them to identify
    # section headings.
    text = re.sub(
        r"[^\S\r\n]+",
        " ",
        text,
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def _find_year(
    text: str,
    filename: str,
):
    match = YEAR_PATTERN.search(
        text[:10000]
    )

    if match:
        return int(match.group(0))

    match = YEAR_PATTERN.search(filename)

    if match:
        return int(match.group(0))

    return None


def parse_pdf_text(paper_id: str):
    paper_id = str(paper_id or "").strip()

    if not ObjectId.is_valid(paper_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid paper ID",
        )

    object_id = ObjectId(paper_id)

    paper = papers_collection.find_one(
        {"_id": object_id}
    )

    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Paper not found",
        )

    filepath = paper.get("filepath")

    if not filepath:
        raise HTTPException(
            status_code=400,
            detail="Paper file path is missing",
        )

    pdf_path = Path(filepath)

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "PDF file does not exist: "
                f"{filepath}"
            ),
        )

    pages = []
    page_texts = []

    try:
        document = pymupdf.open(str(pdf_path))

        try:
            for page_number, page in enumerate(
                document,
                start=1,
            ):
                raw_text = page.get_text(
                    "text"
                ) or ""

                cleaned_text = clean_pdf_text(
                    raw_text
                )

                pages.append(
                    {
                        "page_number": page_number,
                        "text": cleaned_text,
                    }
                )

                if cleaned_text:
                    page_texts.append(
                        cleaned_text
                    )

        finally:
            document.close()

    except Exception as exc:
        papers_collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "status": "uploaded",
                    "parse_error": str(exc),
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "PDF parsing failed: "
                f"{str(exc)}"
            ),
        ) from exc

    combined_text = clean_pdf_text(
        "\n\n".join(page_texts)
    )

    if not combined_text:
        raise HTTPException(
            status_code=400,
            detail=(
                "No readable text was found "
                "in the PDF. The PDF may be "
                "scanned or image-only."
            ),
        )

    title = paper.get("title") or ""

    if title.lower() == "untitled paper":
        title = ""

    if not title:
        title = pdf_path.stem.replace(
            "_",
            " ",
        )

    year = _find_year(
        combined_text,
        paper.get("filename", ""),
    )

    papers_collection.update_one(
        {"_id": object_id},
        {
            "$set": {
                "raw_text": combined_text,
                "text": combined_text,
                "pages": pages,
                "title": title,
                "year": year,
                "status": "parsed",
                "parsed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "parse_error": None,
            }
        },
    )

    return {
        "paper_id": paper_id,
        "status": "parsed",
        "pages_count": len(pages),
        "characters": len(combined_text),
        "year": year,
    }