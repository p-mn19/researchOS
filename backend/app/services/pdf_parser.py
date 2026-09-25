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

AUTHOR_STOP_PATTERN = re.compile(
    r"(?im)^\s*(?:\d+(?:\.\d+)*[.)]?\s*)?abstract\b"
)

AUTHOR_REJECT_TERMS = {
    "abstract",
    "accepted",
    "arxiv",
    "author",
    "copyright",
    "department",
    "email",
    "institute",
    "journal",
    "laboratory",
    "school",
    "university",
}


def _normalise_authors(authors):
    """Return unique, non-empty author names in source order."""
    return list(
        dict.fromkeys(
            " ".join(str(author).split()).strip()
            for author in authors
            if str(author).strip()
        )
    )


def _looks_like_author_name(value: str) -> bool:
    words = value.split()

    if not 2 <= len(words) <= 5:
        return False

    lowered = {word.lower().rstrip(".") for word in words}

    if lowered & AUTHOR_REJECT_TERMS:
        return False

    for word in words:
        # A name token is a capitalised word, a hyphenated/apostrophised
        # capitalised word, or an initial such as "J.". This deliberately
        # rejects affiliations and prose from the title block.
        if not re.fullmatch(
            r"(?:[A-Z]\.?)|(?:[A-Z][A-Za-z'\-]*\.?)+",
            word,
        ):
            return False

    return True


def extract_authors_from_front_matter(text: str):
    """Extract author names from the title block before the abstract.

    PDF metadata is frequently missing or wrong. The title page is the most
    reliable text-only source, so inspect it before content cleaning/chunking
    can discard its layout. This is intentionally conservative: a false
    author is more damaging to a reference than an omitted author.
    """
    if not text:
        return []

    front_matter = text[:6000]
    abstract_match = AUTHOR_STOP_PATTERN.search(front_matter)

    if abstract_match:
        front_matter = front_matter[:abstract_match.start()]

    candidates = []
    seen_content = False

    for raw_line in front_matter.splitlines():
        line = " ".join(raw_line.split()).strip()

        if not line or len(line) > 240:
            continue

        # The first meaningful line is overwhelmingly the paper title. Skip
        # it when it happens to have the same shape as a two-to-five-word
        # personal name (for example, "Deep Learning").
        if not seen_content:
            seen_content = True
            continue

        if (
            "@" in line
            or "http" in line.lower()
            or "doi" in line.lower()
        ):
            continue

        # Remove common affiliation markers such as 1, 2, *, and dagger
        # symbols attached to author names by PDF text extraction.
        line = re.sub(r"[\d*†‡]+", " ", line)
        line = re.sub(r"\s+", " ", line).strip(" ,;·")

        names = re.split(r"\s*(?:,|;|\band\b|&)\s*", line)
        names = [name.strip(" ,;·") for name in names if name.strip(" ,;·")]

        if names and all(_looks_like_author_name(name) for name in names):
            candidates.extend(names)

    return _normalise_authors(candidates)


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

    # Prefer embedded PDF metadata when present, then fall back to the
    # author line in the first page's title block.
    authors = _normalise_authors(
        paper.get("authors") or []
    )

    if not authors:
        authors = extract_authors_from_front_matter(
            page_texts[0] if page_texts else combined_text
        )

    papers_collection.update_one(
        {"_id": object_id},
        {
            "$set": {
                "raw_text": combined_text,
                "text": combined_text,
                "pages": pages,
                "title": title,
                "authors": authors,
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
        "authors": authors,
        "year": year,
    }
