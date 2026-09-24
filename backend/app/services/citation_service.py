from __future__ import annotations

import re
from typing import Iterable, List

from app.schemas.workspace import WorkspaceCitation


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _escape_bibtex(value: object) -> str:
    """
    Escape the small set of characters that commonly break BibTeX fields.

    This does not ask an LLM to construct references. It only serializes
    already-stored workspace citation metadata.
    """
    text = _clean_text(value)

    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }

    for source, replacement in replacements.items():
        text = text.replace(source, replacement)

    return text


def _safe_citation_key(value: object) -> str:
    key = re.sub(
        r"[^A-Za-z0-9:_-]",
        "",
        _clean_text(value),
    )

    return key or "researchos_source"


def _authors_to_bibtex(authors: Iterable[object]) -> str:
    names = [
        _clean_text(author)
        for author in authors
        if _clean_text(author)
    ]

    return " and ".join(names)


def _entry_type(citation: WorkspaceCitation) -> str:
    """
    WorkspaceCitation currently stores title/authors/year/venue/doi but no
    stable publication type. Use @article when venue exists; otherwise @misc.
    """
    return "article" if _clean_text(citation.venue) else "misc"


def citation_to_bibtex(citation: WorkspaceCitation) -> str:
    """Create one deterministic BibTeX entry from one workspace citation."""
    entry_type = _entry_type(citation)
    citation_key = _safe_citation_key(citation.citation_key)
    authors = _authors_to_bibtex(citation.authors)

    fields: List[str] = []

    if authors:
        fields.append(
            f"  author = {{{_escape_bibtex(authors)}}}"
        )

    fields.extend(
        [
            (
                "  title = {"
                f"{_escape_bibtex(citation.title or 'Untitled source')}"
                "}"
            ),
            (
                "  year = {"
                f"{_escape_bibtex(citation.year or 'n.d.')}"
                "}"
            ),
        ]
    )

    venue = _clean_text(citation.venue)
    doi = _clean_text(citation.doi)

    if venue:
        venue_field = "journal" if entry_type == "article" else "howpublished"
        fields.append(
            f"  {venue_field} = {{{_escape_bibtex(venue)}}}"
        )

    if doi:
        fields.append(
            f"  doi = {{{_escape_bibtex(doi)}}}"
        )

    return (
        f"@{entry_type}{{{citation_key},\n"
        + ",\n".join(fields)
        + "\n}"
    )


def build_references_bib(
    citations: Iterable[WorkspaceCitation],
) -> str:
    """
    Create references.bib for a workspace.

    Duplicate citation keys are removed while preserving the first occurrence.
    """
    entries: List[str] = []
    seen_keys: set[str] = set()

    for citation in citations:
        key = _safe_citation_key(citation.citation_key)

        if key in seen_keys:
            continue

        seen_keys.add(key)
        entries.append(citation_to_bibtex(citation))

    return "\n\n".join(entries).strip()
