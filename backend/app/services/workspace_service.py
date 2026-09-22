from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from fastapi import HTTPException
from app.config import settings
from app.services.groq_client import get_groq_client, has_groq_api_keys
from app.db import (
    extractions_collection,
    papers_collection,
    workspace_versions_collection,
    workspaces_collection,
)
from app.schemas.workspace import (
    WorkspaceCitation,
    WorkspaceCreate,
    WorkspaceGenerateRequest,
    WorkspaceGenerationResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
    WorkspaceVersionCreate,
    WorkspaceVersionResponse,
)
from app.services.search_service import semantic_search


CONTENT_TITLES = {
    "research_problem": "Research Problem",
    "research_objectives": "Research Objectives",
    "research_questions": "Research Questions",
    "hypotheses": "Research Hypotheses",
    "related_work": "Related Work",
    "methodology": "Proposed Methodology",
    "proposed_framework": "Proposed Framework",
    "experimental_design": "Experimental Design",
    "evaluation_plan": "Evaluation Plan",
    "expected_contributions": "Expected Contributions",
    "limitations_and_scope": "Limitations and Scope",
    "abstract_draft": "Abstract",
}


CONTENT_QUERIES = {
    "research_problem": (
        "research problem objective limitations future work research gap"
    ),
    "research_objectives": (
        "objective research goal limitations future work"
    ),
    "research_questions": (
        "objective research question limitations future work"
    ),
    "hypotheses": (
        "findings methodology dataset evaluation limitations"
    ),
    "related_work": (
        "methodology approach dataset findings limitations related work"
    ),
    "methodology": (
        "methodology methods approach dataset evaluation metric limitations"
    ),
    "proposed_framework": (
        "methodology approach model framework limitations findings"
    ),
    "experimental_design": (
        "dataset methodology evaluation metric experiment validation"
    ),
    "evaluation_plan": (
        "evaluation metric dataset results validation performance"
    ),
    "expected_contributions": (
        "objective findings limitations future work research gap"
    ),
    "limitations_and_scope": (
        "limitations constraints future work dataset methodology"
    ),
    "abstract_draft": (
        "objective methodology dataset findings limitations research gap"
    ),
}

MAX_PAPER_CONTEXT_CHARS = 3000
MAX_CHUNK_CONTEXT_CHARS = 2500
MAX_INSTRUCTION_CHARS = 600

# Output-token budget for one generated workspace section.
# This is deliberately separate from the model's own maximum.
MIN_GENERATION_TOKENS = 1200
MAX_GENERATION_TOKENS = 8000


SYSTEM_PROMPT = """
You are ResearchOS Workspace, an evidence-grounded academic writing assistant.

Write only from the supplied workspace idea, selected paper metadata,
structured extraction fields, and retrieved passages.

Rules:
1. Treat the workspace idea as a proposed research direction, not an established result.
2. Do not invent citations, datasets, methods, results, metrics, numerical values, or claims.
3. Clearly distinguish reported evidence from proposed work.
4. Use citations only from the allowed citation list.
5. When using internal citations, cite evidence exactly as [paper_id].
6. When using LaTeX citations, cite evidence exactly as \\cite{citation_key}.
7. If evidence is insufficient, say that the selected corpus provides limited evidence.
8. Do not describe a proposed method as already implemented, tested, or evaluated.
9. Do not claim performance improvements, results, or comparisons that do not exist.
10. Use clean academic prose only.
11. Do not use Markdown code fences.
12. Do not add a bibliography because source metadata is returned separately.
13. Complete every sentence and paragraph. Never end the response mid-sentence.
14. Meet the requested target length as closely as the available evidence permits.
""".strip()


def _clean_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return "; ".join(
            _clean_text(item)
            for item in value
            if _clean_text(item)
        )

    if isinstance(value, dict):
        return "; ".join(
            f"{key}: {_clean_text(item)}"
            for key, item in value.items()
            if _clean_text(item)
        )

    return " ".join(str(value).split()).strip()


def _clip_text(value: Any, limit: int) -> str:
    text = _clean_text(value)

    if len(text) <= limit:
        return text

    clipped = text[:limit]

    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]

    return f"{clipped}..."


def _safe_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []

    return [
        _clean_text(item)
        for item in value
        if _clean_text(item)
    ]


def _validate_workspace_id(workspace_id: str) -> ObjectId:
    workspace_id = str(workspace_id or "").strip()

    if not ObjectId.is_valid(workspace_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid workspace ID",
        )

    return ObjectId(workspace_id)


def _normalise_paper_ids(paper_ids: List[str]) -> List[str]:
    return list(
        dict.fromkeys(
            str(paper_id).strip()
            for paper_id in paper_ids
            if str(paper_id).strip()
        )
    )


def _paper_query(paper_ids: List[str]) -> Dict[str, Any]:
    object_ids = [
        ObjectId(paper_id)
        for paper_id in paper_ids
        if ObjectId.is_valid(paper_id)
    ]

    clauses: List[Dict[str, Any]] = []

    if object_ids:
        clauses.append(
            {
                "_id": {
                    "$in": object_ids,
                }
            }
        )

    if paper_ids:
        clauses.append(
            {
                "id": {
                    "$in": paper_ids,
                }
            }
        )

    if not clauses:
        return {
            "_id": {
                "$in": [],
            }
        }

    return {
        "$or": clauses,
    }


def _citation_key(
    paper: Dict[str, Any],
    paper_id: str,
) -> str:
    authors = paper.get("authors") or []
    author_name = "research"

    if authors:
        first_author = str(authors[0]).strip()

        if first_author:
            author_name = (
                first_author.split()[-1]
                or "research"
            )

    author_name = re.sub(
        r"[^A-Za-z0-9]",
        "",
        author_name,
    ).lower()

    year = str(paper.get("year") or "nd")

    title = str(
        paper.get("title")
        or paper.get("filename")
        or "paper"
    )

    title_words = re.findall(
        r"[A-Za-z0-9]+",
        title.lower(),
    )[:2]

    title_part = "".join(title_words) or "paper"

    suffix = re.sub(
        r"[^A-Za-z0-9]",
        "",
        paper_id,
    )[-6:] or "source"

    return (
        f"{author_name}{year}"
        f"{title_part}{suffix}"
    )


def _serialize_workspace(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "title": document.get("title", ""),
        "description": document.get("description", ""),
        "paper_ids": document.get("paper_ids", []),
        "idea": document.get("idea", {}),
        "research_objective": document.get(
            "research_objective",
            "",
        ),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
    }


def _serialize_version(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "workspace_id": document.get("workspace_id", ""),
        "content_type": document.get("content_type"),
        "content_markdown": document.get(
            "content_markdown",
            "",
        ),
        "latex_code": document.get(
            "latex_code",
            "",
        ),
        "citations": document.get("citations", []),
        "warnings": document.get("warnings", []),
        "source_chunk_ids": document.get(
            "source_chunk_ids",
            [],
        ),
        "version": document.get("version", 1),
        "created_at": document.get("created_at"),
    }


def create_workspace(
    payload: WorkspaceCreate,
) -> WorkspaceResponse:
    paper_ids = _normalise_paper_ids(payload.paper_ids)

    if not paper_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "Select at least one paper "
                "for the workspace."
            ),
        )

    found_papers = list(
        papers_collection.find(
            _paper_query(paper_ids)
        )
    )

    found_ids = {
        str(paper["_id"])
        for paper in found_papers
    }

    missing_ids = [
        paper_id
        for paper_id in paper_ids
        if paper_id not in found_ids
    ]

    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=(
                "Selected papers not found: "
                f"{', '.join(missing_ids)}"
            ),
        )

    now = datetime.utcnow()

    document = {
        "title": payload.title.strip(),
        "description": payload.description.strip(),
        "paper_ids": paper_ids,
        "idea": payload.idea.model_dump(),
        "research_objective": (
            payload.research_objective.strip()
        ),
        "created_at": now,
        "updated_at": now,
    }

    result = workspaces_collection.insert_one(document)
    document["_id"] = result.inserted_id

    return WorkspaceResponse(
        **_serialize_workspace(document)
    )


def list_workspaces() -> List[WorkspaceResponse]:
    documents = workspaces_collection.find().sort(
        "updated_at",
        -1,
    )

    return [
        WorkspaceResponse(
            **_serialize_workspace(document)
        )
        for document in documents
    ]


def get_workspace(
    workspace_id: str,
) -> WorkspaceResponse:
    object_id = _validate_workspace_id(workspace_id)

    document = workspaces_collection.find_one(
        {
            "_id": object_id,
        }
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    return WorkspaceResponse(
        **_serialize_workspace(document)
    )


def _get_workspace_document(
    workspace_id: str,
) -> Dict[str, Any]:
    object_id = _validate_workspace_id(workspace_id)

    document = workspaces_collection.find_one(
        {
            "_id": object_id,
        }
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    return document


def update_workspace(
    workspace_id: str,
    payload: WorkspaceUpdate,
) -> WorkspaceResponse:
    object_id = _validate_workspace_id(workspace_id)

    updates = payload.model_dump(exclude_unset=True)

    if "paper_ids" in updates:
        paper_ids = _normalise_paper_ids(
            updates["paper_ids"] or []
        )

        if not paper_ids:
            raise HTTPException(
                status_code=400,
                detail=(
                    "A workspace must include "
                    "at least one paper."
                ),
            )

        found_papers = list(
            papers_collection.find(
                _paper_query(paper_ids)
            )
        )

        found_ids = {
            str(paper["_id"])
            for paper in found_papers
        }

        missing_ids = [
            paper_id
            for paper_id in paper_ids
            if paper_id not in found_ids
        ]

        if missing_ids:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Selected papers not found: "
                    f"{', '.join(missing_ids)}"
                ),
            )

        updates["paper_ids"] = paper_ids

    if "idea" in updates and updates["idea"] is not None:
        updates["idea"] = payload.idea.model_dump()

    for field in (
        "title",
        "description",
        "research_objective",
    ):
        if field in updates and isinstance(
            updates[field],
            str,
        ):
            updates[field] = updates[field].strip()

    if not updates:
        return get_workspace(workspace_id)

    updates["updated_at"] = datetime.utcnow()

    workspaces_collection.update_one(
        {
            "_id": object_id,
        },
        {
            "$set": updates,
        },
    )

    return get_workspace(workspace_id)


def _get_workspace_papers(
    paper_ids: List[str],
) -> List[Dict[str, Any]]:
    papers = list(
        papers_collection.find(
            _paper_query(paper_ids)
        )
    )

    if not papers:
        raise HTTPException(
            status_code=404,
            detail=(
                "No workspace papers could be found."
            ),
        )

    paper_map = {
        str(paper["_id"]): paper
        for paper in papers
    }

    extractions = list(
        extractions_collection.find(
            {
                "paper_id": {
                    "$in": list(paper_map.keys()),
                }
            }
        )
    )

    extraction_map = {
        str(extraction.get("paper_id")): extraction
        for extraction in extractions
        if extraction.get("paper_id")
    }

    records: List[Dict[str, Any]] = []

    for paper_id in paper_ids:
        paper = paper_map.get(paper_id)

        if not paper:
            continue

        extraction = extraction_map.get(
            paper_id,
            {},
        )

        records.append(
            {
                "paper_id": paper_id,
                "title": (
                    paper.get("title")
                    or paper.get("filename")
                    or "Untitled paper"
                ),
                "authors": paper.get("authors") or [],
                "year": paper.get("year"),
                "venue": paper.get("venue"),
                "doi": paper.get("doi"),
                "citation_key": _citation_key(
                    paper,
                    paper_id,
                ),
                "abstract": _clean_text(
                    paper.get("abstract")
                ),
                "objective": _clean_text(
                    extraction.get("objective")
                    or paper.get("objective")
                ),
                "methodology": _clean_text(
                    extraction.get("methodology")
                    or paper.get("methodology")
                ),
                "dataset": _clean_text(
                    extraction.get("dataset")
                    or paper.get("dataset")
                ),
                "evaluation_metric": _clean_text(
                    extraction.get("evaluation_metric")
                    or paper.get("evaluation_metric")
                ),
                "limitations": _clean_text(
                    extraction.get("limitations")
                    or paper.get("limitations")
                ),
                "future_work": _clean_text(
                    extraction.get("future_work")
                    or paper.get("future_work")
                ),
                "research_gap": _clean_text(
                    extraction.get("research_gap")
                    or paper.get("research_gap")
                ),
                "findings": _clean_text(
                    extraction.get("findings")
                    or paper.get("findings")
                ),
                "keywords": _safe_list(
                    extraction.get("keywords")
                    or paper.get("keywords")
                ),
            }
        )

    if not records:
        raise HTTPException(
            status_code=404,
            detail=(
                "No valid papers were available "
                "in this workspace."
            ),
        )

    return records


def _build_paper_context(
    papers: List[Dict[str, Any]],
) -> str:
    blocks: List[str] = []
    used_chars = 0

    for paper in papers:
        block = "\n".join(
            [
                f"PAPER ID: {paper['paper_id']}",
                f"CITATION KEY: {paper['citation_key']}",
                f"TITLE: {paper['title']}",
                (
                    "ABSTRACT: "
                    f"{_clip_text(paper['abstract'], 550) or 'Not available'}"
                ),
                (
                    "OBJECTIVE: "
                    f"{_clip_text(paper['objective'], 350) or 'Not available'}"
                ),
                (
                    "METHODOLOGY: "
                    f"{_clip_text(paper['methodology'], 350) or 'Not available'}"
                ),
                (
                    "DATASET: "
                    f"{_clip_text(paper['dataset'], 220) or 'Not available'}"
                ),
                (
                    "FINDINGS: "
                    f"{_clip_text(paper['findings'], 350) or 'Not available'}"
                ),
                (
                    "LIMITATIONS: "
                    f"{_clip_text(paper['limitations'], 400) or 'Not available'}"
                ),
                (
                    "FUTURE WORK / GAP: "
                    f"{_clip_text(paper['future_work'] or paper['research_gap'], 350) or 'Not available'}"
                ),
            ]
        )

        remaining = (
            MAX_PAPER_CONTEXT_CHARS - used_chars
        )

        if remaining <= 0:
            break

        if len(block) > remaining:
            blocks.append(block[:remaining])
            break

        blocks.append(block)
        used_chars += len(block) + 6

    return "\n\n---\n\n".join(blocks)


def _retrieve_evidence(
    paper_ids: List[str],
    content_type: str,
) -> List[Dict[str, Any]]:
    query = CONTENT_QUERIES.get(
        content_type,
        (
            "objective methodology findings "
            "limitations future work"
        ),
    )

    try:
        return semantic_search(
            query=query,
            paper_ids=paper_ids,
            top_k=min(
                6,
                max(3, len(paper_ids) * 2),
            ),
        )
    except Exception:
        return []


def _build_chunk_context(
    chunks: List[Dict[str, Any]],
) -> str:
    blocks: List[str] = []
    used_chars = 0

    for chunk in chunks:
        paper_id = str(
            chunk.get("paper_id") or ""
        ).strip()

        text = _clean_text(chunk.get("text"))

        if not paper_id or not text:
            continue

        section = _clean_text(
            chunk.get("section_title")
        ) or "Unknown section"

        page = (
            chunk.get("page")
            or chunk.get("page_number")
        )

        location = (
            f", page {page}"
            if page is not None
            else ""
        )

        block = "\n".join(
            [
                f"PAPER ID: {paper_id}",
                f"LOCATION: {section}{location}",
                (
                    "EVIDENCE: "
                    f"{_clip_text(text, 550)}"
                ),
            ]
        )

        remaining = (
            MAX_CHUNK_CONTEXT_CHARS - used_chars
        )

        if remaining <= 0:
            break

        if len(block) > remaining:
            blocks.append(block[:remaining])
            break

        blocks.append(block)
        used_chars += len(block) + 6

    return "\n\n---\n\n".join(blocks)


def _build_citations(
    papers: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
) -> Tuple[List[WorkspaceCitation], List[str]]:
    chunk_locations: Dict[str, Dict[str, Any]] = {}
    source_chunk_ids: List[str] = []

    for chunk in chunks:
        paper_id = str(
            chunk.get("paper_id") or ""
        ).strip()

        if (
            paper_id
            and paper_id not in chunk_locations
        ):
            chunk_locations[paper_id] = chunk

        chunk_id = str(
            chunk.get("id") or ""
        ).strip()

        if chunk_id:
            source_chunk_ids.append(chunk_id)

    citations: List[WorkspaceCitation] = []

    for paper in papers:
        location = chunk_locations.get(
            paper["paper_id"],
            {},
        )

        citations.append(
            WorkspaceCitation(
                paper_id=paper["paper_id"],
                title=paper["title"],
                authors=paper["authors"],
                year=paper["year"],
                venue=paper.get("venue"),
                doi=paper.get("doi"),
                citation_key=paper["citation_key"],
                section_title=location.get(
                    "section_title"
                ),
                page=(
                    location.get("page")
                    or location.get("page_number")
                ),
            )
        )

    return (
        citations,
        list(dict.fromkeys(source_chunk_ids)),
    )


def _replace_internal_citations(
    text: str,
    citations: List[WorkspaceCitation],
) -> str:
    for citation in citations:
        text = text.replace(
            f"[{citation.paper_id}]",
            f"\\cite{{{citation.citation_key}}}",
        )

    return text


def _latex_escape(text: str) -> str:
    text = str(text or "")

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


def _markdown_to_latex(
    markdown: str,
    title: str,
    citations: List[WorkspaceCitation],
) -> str:
    text = _replace_internal_citations(
        markdown.strip(),
        citations,
    )

    citation_tokens: Dict[str, str] = {}

    for index, citation in enumerate(citations):
        token = f"@@CITATION_{index}@@"
        command = (
            f"\\cite{{{citation.citation_key}}}"
        )

        text = text.replace(command, token)
        citation_tokens[token] = command

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(
            r"\n\s*\n",
            text,
        )
        if paragraph.strip()
    ]

    latex_parts = [
        f"\\section{{{_latex_escape(title)}}}"
    ]

    for paragraph in paragraphs:
        lines = paragraph.splitlines()

        is_list = (
            bool(lines)
            and all(
                re.match(
                    r"^\s*(?:[-*]|\d+[.)])\s+",
                    line,
                )
                for line in lines
            )
        )

        if is_list:
            latex_parts.append("\\begin{itemize}")

            for line in lines:
                item = re.sub(
                    r"^\s*(?:[-*]|\d+[.)])\s+",
                    "",
                    line,
                ).strip()

                escaped = _latex_escape(item)

                for token, command in citation_tokens.items():
                    escaped = escaped.replace(
                        token,
                        command,
                    )

                latex_parts.append(
                    f"  \\item {escaped}"
                )

            latex_parts.append("\\end{itemize}")
            continue

        heading = re.match(
            r"^#{1,6}\s+(.+)$",
            paragraph,
        )

        if heading:
            escaped = (
                "\\subsection{"
                + _latex_escape(
                    heading.group(1)
                )
                + "}"
            )
        else:
            escaped = _latex_escape(paragraph)

        for token, command in citation_tokens.items():
            escaped = escaped.replace(
                token,
                command,
            )

        latex_parts.append(escaped)

    return "\n\n".join(latex_parts)


def _build_bibtex(
    citations: List[WorkspaceCitation],
) -> str:
    entries: List[str] = []

    for citation in citations:
        authors = " and ".join(
            str(author).strip()
            for author in citation.authors
            if str(author).strip()
        ) or "Unknown"

        title = (
            str(citation.title or "Untitled")
            .replace("{", "")
            .replace("}", "")
        )

        fields = [
            f"  author = {{{authors}}}",
            f"  title = {{{title}}}",
            f"  year = {{{citation.year or 'n.d.'}}}",
        ]

        if citation.venue:
            fields.append(
                f"  journal = {{{citation.venue}}}"
            )

        if citation.doi:
            fields.append(
                f"  doi = {{{citation.doi}}}"
            )

        entries.append(
            "@article{"
            + citation.citation_key
            + ",\n"
            + ",\n".join(fields)
            + "\n}"
        )

    return "\n\n".join(entries)


def _build_prompt(
    workspace: Dict[str, Any],
    request: WorkspaceGenerateRequest,
    papers: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
) -> str:
    idea = workspace.get("idea") or {}

    content_type = str(
        request.content_type or "related_work"
    )

    title = CONTENT_TITLES.get(
        content_type,
        "Research Workspace Section",
    )

    citation_lines = "\n".join(
        (
            f"- [{paper['paper_id']}] maps to "
            f"\\cite{{{paper['citation_key']}}}: "
            f"{paper['title']}"
        )
        for paper in papers
    )

    citation_rule = (
        "Use internal citations exactly as [paper_id]."
        if request.citation_style == "internal"
        else (
            "Use LaTeX citations exactly as "
            "\\cite{citation_key}."
        )
    )

    return f"""
Write the academic section: {title}.

Target length:
Approximately {request.target_word_count} words.

Workspace title:
{_clip_text(workspace.get('title'), 300)}

Workspace research objective:
{_clip_text(workspace.get('research_objective'), 600) or 'Not specified'}

Selected research idea:
Title: {_clip_text(idea.get('title'), 300)}
Problem statement: {_clip_text(idea.get('problem_statement'), 700)}
Hypothesis: {_clip_text(idea.get('hypothesis'), 400)}
Recommended methodology: {_clip_text(idea.get('recommended_methodology'), 500)}
Expected contribution: {_clip_text(idea.get('expected_contribution'), 500)}

Citation rule:
{citation_rule}

Allowed citations:
{_clip_text(citation_lines, 2000)}

Selected paper metadata and extracted evidence:
{_build_paper_context(papers)}

Retrieved paper passages:
{_build_chunk_context(chunks) or 'No passage-level evidence was retrieved. Use cautious language and only use available structured metadata.'}

Additional instructions:
{_clip_text(request.instructions, MAX_INSTRUCTION_CHARS) or 'No additional instructions.'}

Write only the requested section.
Do not add a bibliography.
Do not use a Markdown code block.
Write the complete section before finishing. Do not end with an incomplete sentence, incomplete paragraph, or a dangling transition such as "Consequently,".
""".strip()


def _generation_warnings(
    papers: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
) -> List[str]:
    warnings: List[str] = []

    if not chunks:
        warnings.append(
            "No chunk-level evidence passages were retrieved. "
            "The output is grounded primarily in stored paper "
            "metadata and extraction fields."
        )

    incomplete_papers = [
        paper["title"]
        for paper in papers
        if not any(
            paper.get(field)
            for field in (
                "objective",
                "methodology",
                "limitations",
                "future_work",
                "findings",
            )
        )
    ]

    if incomplete_papers:
        warnings.append(
            "Some selected papers have limited extracted fields: "
            + ", ".join(incomplete_papers[:3])
            + "."
        )

    warnings.append(
        "Generated content is a proposed-study draft. "
        "Verify all claims, citations, methods, LaTeX, and "
        "academic formatting before use."
    )

    return warnings


def _is_rate_limit_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    text = str(exc).lower()

    return (
        status_code == 429
        or "rate limit" in text
        or "rate_limit" in text
        or "tokens per minute" in text
        or "status code: 429" in text
    )


def _call_groq(
    prompt: str,
    max_tokens: int,
) -> str:
    if not has_groq_api_keys():
        raise HTTPException(
            status_code=500,
            detail=(
                "GROQ_API_KEY or GROQ_API_KEYS is missing. Add it to backend/.env "
                "and restart the backend."
            ),
        )

    last_error: Optional[Exception] = None

    for attempt in range(2):
        try:
            client = get_groq_client(timeout=90.0, max_retries=1)
            assert client is not None
            completion = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                temperature=0.2,
                max_tokens=max_tokens,
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

            if not completion.choices:
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Groq returned no generation choices."
                    ),
                )

            choice = completion.choices[0]
            content = (choice.message.content or "").strip()
            finish_reason = str(
                getattr(choice, "finish_reason", "") or ""
            ).lower()

            if not content:
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Groq returned an empty generation."
                    ),
                )

            if finish_reason == "length":
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "The model reached the requested output-token budget "
                        f"({max_tokens} tokens) before completing the section. "
                        "Use a shorter word target, generate the document section "
                        "by section, or increase MAX_GENERATION_TOKENS if the "
                        "configured Groq model supports a larger completion."
                    ),
                )

            return content

        except HTTPException:
            raise

        except Exception as exc:
            last_error = exc

            if _is_rate_limit_error(exc) and attempt == 0:
                time.sleep(8)
                continue

            raise HTTPException(
                status_code=502,
                detail=(
                    "Workspace generation failed. "
                    f"Error type: {type(exc).__name__}. "
                    f"Details: {str(exc)}"
                ),
            ) from exc

    raise HTTPException(
        status_code=502,
        detail=(
            "Workspace generation failed after retry. "
            f"Error type: {type(last_error).__name__ if last_error else 'UnknownError'}. "
            f"Details: {str(last_error) if last_error else 'No detail available'}"
        ),
    )


def generate_workspace_content(
    workspace_id: str,
    request: WorkspaceGenerateRequest,
) -> WorkspaceGenerationResponse:
    if not request.content_type:
        raise HTTPException(
            status_code=400,
            detail=(
                "content_type is required for section generation."
            ),
        )

    workspace = _get_workspace_document(workspace_id)

    paper_ids = _normalise_paper_ids(
        workspace.get("paper_ids") or []
    )

    if not paper_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "This workspace does not have selected papers."
            ),
        )

    papers = _get_workspace_papers(paper_ids)

    chunks = _retrieve_evidence(
        paper_ids,
        str(request.content_type),
    )

    citations, source_chunk_ids = _build_citations(
        papers,
        chunks,
    )

    prompt = _build_prompt(
        workspace,
        request,
        papers,
        chunks,
    )

    requested_words = max(
        1,
        int(request.target_word_count),
    )

    # Academic prose, citations, and cautious wording can require
    # substantially more tokens than a basic word-to-token estimate.
    generation_tokens = min(
        MAX_GENERATION_TOKENS,
        max(
            MIN_GENERATION_TOKENS,
            int(requested_words * 2.75) + 500,
        ),
    )

    print(
        "[Workspace generation]",
        {
            "target_word_count": requested_words,
            "max_tokens": generation_tokens,
            "model": settings.GROQ_MODEL,
        },
    )
    content_markdown = _call_groq(
        prompt=prompt,
        max_tokens=generation_tokens,
    )

    title = CONTENT_TITLES.get(
        str(request.content_type),
        "Research Workspace Section",
    )

    latex_code = ""

    if request.generate_latex:
        latex_code = _markdown_to_latex(
            markdown=content_markdown,
            title=title,
            citations=citations,
        )

    return WorkspaceGenerationResponse(
        workspace_id=workspace_id,
        content_type=request.content_type,
        title=title,
        content_markdown=content_markdown,
        latex_code=latex_code,
        citations=citations,
        warnings=_generation_warnings(
            papers,
            chunks,
        ),
        source_chunk_ids=source_chunk_ids,
        model=settings.GROQ_MODEL,
    )


def create_workspace_version(
    workspace_id: str,
    payload: WorkspaceVersionCreate,
) -> WorkspaceVersionResponse:
    _get_workspace_document(workspace_id)

    now = datetime.utcnow()

    latest = workspace_versions_collection.find_one(
        {
            "workspace_id": workspace_id,
        },
        sort=[
            ("version", -1),
        ],
    )

    version_number = (
        int(latest.get("version", 0)) + 1
        if latest
        else 1
    )

    document = {
        "workspace_id": workspace_id,
        "content_type": payload.content_type,
        "content_markdown": payload.content_markdown,
        "latex_code": payload.latex_code,
        "citations": [
            citation.model_dump()
            for citation in payload.citations
        ],
        "warnings": payload.warnings,
        "source_chunk_ids": payload.source_chunk_ids,
        "version": version_number,
        "created_at": now,
    }

    result = workspace_versions_collection.insert_one(
        document
    )

    document["_id"] = result.inserted_id

    workspaces_collection.update_one(
        {
            "_id": _validate_workspace_id(
                workspace_id
            ),
        },
        {
            "$set": {
                "updated_at": now,
            },
        },
    )

    return WorkspaceVersionResponse(
        **_serialize_version(document)
    )


def list_workspace_versions(
    workspace_id: str,
) -> List[WorkspaceVersionResponse]:
    _get_workspace_document(workspace_id)

    documents = workspace_versions_collection.find(
        {
            "workspace_id": workspace_id,
        }
    ).sort(
        "version",
        -1,
    )

    return [
        WorkspaceVersionResponse(
            **_serialize_version(document)
        )
        for document in documents
    ]
