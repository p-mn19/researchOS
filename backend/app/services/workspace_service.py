import json
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from fastapi import HTTPException
from groq import Groq

from app.config import settings
from app.db import (
    extractions_collection,
    papers_collection,
    workspace_versions_collection,
    workspaces_collection,
)
from app.schemas.workspace import (
    FullPaperOutline,
    FullPaperSectionPlan,
    WorkspaceCitation,
    WorkspaceCreate,
    WorkspaceGenerateRequest,
    WorkspaceGenerationResponse,
    WorkspaceResponse,
    WorkspaceSectionResult,
    WorkspaceUpdate,
    WorkspaceVersionCreate,
    WorkspaceVersionResponse,
)
from app.services.search_service import semantic_search


client = None

if settings.GROQ_API_KEY.strip():
    client = Groq(
        api_key=settings.GROQ_API_KEY.strip(),
        base_url="https://api.groq.com",
        timeout=90.0,
        # Rate-limit retries are handled below so a full-paper job can honour
        # the provider's retry window instead of issuing another immediate
        # request for every remaining section.
        max_retries=0,
    )


CONTENT_TITLES = {
    "introduction": "Introduction",
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
    "conclusion": "Conclusion",
}


CONTENT_QUERIES = {
    "introduction": (
        "research domain motivation objective research gap limitations"
    ),
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
    "conclusion": (
        "objective research gap methodology limitations future work"
    ),
}


FULL_PAPER_SECTION_ORDER = [
    {
        "key": "introduction",
        "title": "Introduction",
        "purpose": (
            "Introduce the research domain, motivation, selected corpus, "
            "and the candidate problem direction."
        ),
        "weight": 0.12,
    },
    {
        "key": "research_problem",
        "title": "Research Problem",
        "purpose": (
            "Define the candidate research problem from corpus limitations "
            "and research-gap evidence."
        ),
        "weight": 0.08,
    },
    {
        "key": "research_objectives",
        "title": "Research Objectives",
        "purpose": (
            "State clear and achievable objectives for the proposed study."
        ),
        "weight": 0.06,
    },
    {
        "key": "research_questions",
        "title": "Research Questions",
        "purpose": (
            "Formulate answerable research questions aligned with the "
            "selected idea and objectives."
        ),
        "weight": 0.06,
    },
    {
        "key": "hypotheses",
        "title": "Research Hypotheses",
        "purpose": (
            "State testable proposed hypotheses without presenting them "
            "as established findings."
        ),
        "weight": 0.06,
    },
    {
        "key": "related_work",
        "title": "Related Work",
        "purpose": (
            "Synthesize prior approaches, datasets, findings, and "
            "limitations across the selected literature."
        ),
        "weight": 0.22,
    },
    {
        "key": "proposed_methodology",
        "title": "Proposed Methodology",
        "purpose": (
            "Describe the proposed methodology and clearly distinguish "
            "it from methods reported by source papers."
        ),
        "weight": 0.15,
    },
    {
        "key": "proposed_framework",
        "title": "Proposed Framework",
        "purpose": (
            "Describe the proposed framework components, inputs, process, "
            "and expected output."
        ),
        "weight": 0.08,
    },
    {
        "key": "experimental_design",
        "title": "Experimental Design",
        "purpose": (
            "Describe planned experiments, baselines, controls, datasets, "
            "and validation logic."
        ),
        "weight": 0.08,
    },
    {
        "key": "evaluation_plan",
        "title": "Evaluation Plan",
        "purpose": (
            "Specify proposed metrics and evaluation procedures informed "
            "by the selected literature."
        ),
        "weight": 0.06,
    },
    {
        "key": "expected_contributions",
        "title": "Expected Contributions",
        "purpose": (
            "State expected contributions cautiously as proposed outcomes."
        ),
        "weight": 0.05,
    },
    {
        "key": "limitations_and_scope",
        "title": "Limitations and Scope",
        "purpose": (
            "State likely scope boundaries, anticipated limitations, and "
            "validation constraints."
        ),
        "weight": 0.04,
    },
    {
        "key": "conclusion",
        "title": "Conclusion",
        "purpose": (
            "Summarize the proposed study without claiming unperformed "
            "experimental results."
        ),
        "weight": 0.04,
    },
]


# Keep an individual Groq request comfortably below the 8K TPM allowance used
# by the default on-demand tier.  The old prompt sent every extraction field
# and up to sixteen long chunks for every section, so even short sections could
# request more than the provider permits.
MAX_PROMPT_PAPER_CHARS = 2_400
MAX_PROMPT_CHUNK_CHARS = 2_000
MAX_PROMPT_INSTRUCTION_CHARS = 500


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
10. Use clean academic prose only. Do not use Markdown code fences.
11. Do not add a bibliography because source metadata is returned separately.
""".strip()


OUTLINE_SYSTEM_PROMPT = """
You are ResearchOS Workspace Outline Planner.

Build a concise, evidence-aware outline for a proposed research paper.
Use only the supplied workspace idea and selected paper evidence.

Rules:
1. The paper is a proposed study; do not include results or claims of completed evaluation.
2. Use only the supplied paper IDs.
3. Do not invent datasets, methods, metrics, citations, or findings.
4. Return valid JSON only, without Markdown fences or explanatory text.
5. Return exactly the requested object keys.
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
    """Return a clean prompt-safe excerpt without cutting a word when possible."""
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def _safe_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []

    return [
        _clean_text(item)
        for item in value
        if _clean_text(item)
    ]


def _parse_json(content: str) -> Dict[str, Any]:
    content = (content or "").strip()

    if content.startswith("```"):
        content = re.sub(
            r"^```(?:json)?",
            "",
            content,
            flags=re.IGNORECASE,
        )
        content = re.sub(r"```$", "", content).strip()

    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")

        if start < 0 or end <= start:
            return {}

        try:
            parsed = json.loads(content[start:end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


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
        clauses.append({"_id": {"$in": object_ids}})

    if paper_ids:
        clauses.append({"id": {"$in": paper_ids}})

    return {"$or": clauses} if clauses else {"_id": {"$in": []}}


def _citation_key(
    paper: Dict[str, Any],
    paper_id: str,
) -> str:
    authors = paper.get("authors") or []
    author_name = "research"

    if authors:
        author_name = str(authors).split()[-1] or "research"[0]

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

    words = re.findall(
        r"[A-Za-z0-9]+",
        title.lower(),
    )[:2]

    title_part = "".join(words) or "paper"
    suffix = re.sub(
        r"[^a-zA-Z0-9]",
        "",
        paper_id,
    )[-6:] or "source"

    return f"{author_name}{year}{title_part}{suffix}"


def _serialize_workspace(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "title": doc.get("title", ""),
        "description": doc.get("description", ""),
        "paper_ids": doc.get("paper_ids", []),
        "idea": doc.get("idea", {}),
        "research_objective": doc.get(
            "research_objective",
            "",
        ),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


def _serialize_version(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "workspace_id": doc.get("workspace_id", ""),
        "generation_mode": doc.get(
            "generation_mode",
            "section",
        ),
        "content_type": doc.get("content_type"),
        "content_markdown": doc.get(
            "content_markdown",
            "",
        ),
        "latex_code": doc.get("latex_code", ""),
        "citations": doc.get("citations", []),
        "warnings": doc.get("warnings", []),
        "source_chunk_ids": doc.get(
            "source_chunk_ids",
            [],
        ),
        "outline": doc.get("outline"),
        "sections": doc.get("sections", []),
        "full_paper_markdown": doc.get(
            "full_paper_markdown",
            "",
        ),
        "full_paper_latex": doc.get(
            "full_paper_latex",
            "",
        ),
        "bibtex": doc.get("bibtex", ""),
        "version": doc.get("version", 1),
        "created_at": doc.get("created_at"),
    }


def create_workspace(
    payload: WorkspaceCreate,
) -> WorkspaceResponse:
    paper_ids = _normalise_paper_ids(payload.paper_ids)

    if not paper_ids:
        raise HTTPException(
            status_code=400,
            detail="Select at least one paper for the workspace.",
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
        {"_id": object_id}
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
        {"_id": object_id}
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

        found = list(
            papers_collection.find(
                _paper_query(paper_ids)
            )
        )

        found_ids = {
            str(paper["_id"])
            for paper in found
        }

        missing = [
            paper_id
            for paper_id in paper_ids
            if paper_id not in found_ids
        ]

        if missing:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Selected papers not found: "
                    f"{', '.join(missing)}"
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
        {"_id": object_id},
        {"$set": updates},
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
            detail="No workspace papers could be found.",
        )

    paper_map = {
        str(paper["_id"]): paper
        for paper in papers
    }

    extractions = list(
        extractions_collection.find(
            {
                "paper_id": {
                    "$in": list(paper_map.keys())
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
    max_chars: int = MAX_PROMPT_PAPER_CHARS,
) -> str:
    blocks: List[str] = []
    used_chars = 0

    for paper in papers:
        block = "\n".join(
            [
                f"PAPER ID: {paper['paper_id']}",
                f"CITATION KEY: {paper['citation_key']}",
                f"TITLE: {paper['title']}",
                f"YEAR: {paper['year'] or 'Not available'}",
                f"ABSTRACT: {paper['abstract'][:700] or 'Not available'}",
                f"OBJECTIVE: {paper['objective'][:450] or 'Not available'}",
                f"METHODOLOGY: {paper['methodology'][:450] or 'Not available'}",
                f"FINDINGS: {paper['findings'][:450] or 'Not available'}",
                f"LIMITATIONS / GAP: {(paper['limitations'] or paper['research_gap'] or paper['future_work'])[:500] or 'Not available'}",
            ]
        )

        remaining = max_chars - used_chars
        if remaining <= 0:
            break

        if len(block) > remaining:
            blocks.append(block[:remaining].rsplit("\n", 1)[0])
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

    return semantic_search(
        query=query,
        paper_ids=paper_ids,
        top_k=min(8, max(4, len(paper_ids) * 2)),
    )


def _build_chunk_context(
    chunks: List[Dict[str, Any]],
    max_chars: int = MAX_PROMPT_CHUNK_CHARS,
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

        source_id = str(chunk.get("id") or "")
        title = _clean_text(
            chunk.get("paper_title")
        ) or "Untitled paper"

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
                f"EVIDENCE: {text[:650]}",
            ]
        )
        remaining = max_chars - used_chars
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
        )

        if paper_id and paper_id not in chunk_locations:
            chunk_locations[paper_id] = chunk

        chunk_id = str(chunk.get("id") or "").strip()

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


def _replace_internal_citations(
    text: str,
    citations: List[WorkspaceCitation],
) -> str:
    citation_map = {
        citation.paper_id: citation.citation_key
        for citation in citations
    }

    for paper_id, citation_key in citation_map.items():
        text = text.replace(
            f"[{paper_id}]",
            f"\\cite{{{citation_key}}}",
        )

    return text


def _markdown_to_latex_section(
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
        command = f"\\cite{{{citation.citation_key}}}"
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

    latex_parts = [f"\\section{{{_latex_escape(title)}}}"]

    for paragraph in paragraphs:
        lines = paragraph.splitlines()

        if (
            lines
            and all(
                re.match(r"^\s*(?:[-*]|\d+[.)])\s+", line)
                for line in lines
            )
        ):
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

        # Markdown headings are content, not literal hash characters in the
        # LaTeX document.  A section title already has its own \section.
        heading = re.match(r"^#{1,6}\s+(.+)$", paragraph)
        if heading:
            escaped = f"\\subsection{{{_latex_escape(heading.group(1))}}}"
        else:
            escaped = _latex_escape(paragraph)

        for token, command in citation_tokens.items():
            escaped = escaped.replace(
                token,
                command,
            )

        latex_parts.append(escaped)

    return "\n\n".join(latex_parts)


def _bibtex_escape(value: str) -> str:
    return (
        str(value or "")
        .replace("\\", "")
        .replace("{", "")
        .replace("}", "")
        .replace("\n", " ")
        .strip()
    )


def _build_bibtex(
    citations: List[WorkspaceCitation],
) -> str:
    entries: List[str] = []

    for citation in citations:
        authors = " and ".join(
            _bibtex_escape(author)
            for author in citation.authors
            if _bibtex_escape(author)
        ) or "Unknown"

        title = _bibtex_escape(citation.title) or "Untitled"
        year = str(citation.year or "n.d.")

        fields = [
            f"  author = {{{authors}}}",
            f"  title = {{{title}}}",
            f"  year = {{{year}}}",
        ]

        if citation.venue:
            fields.append(
                f"  journal = {{{_bibtex_escape(citation.venue)}}}"
            )

        if citation.doi:
            fields.append(
                f"  doi = {{{_bibtex_escape(citation.doi)}}}"
            )

        entries.append(
            "@article{"
            + citation.citation_key
            + ",\n"
            + ",\n".join(fields)
            + "\n}"
        )

    return "\n\n".join(entries)


def _full_paper_latex(
    workspace: Dict[str, Any],
    sections: List[WorkspaceSectionResult],
    citations: List[WorkspaceCitation],
) -> str:
    title = _latex_escape(
        workspace.get("title")
        or "ResearchOS Workspace Draft"
    )

    abstract = next(
        (
            section.latex_code
            for section in sections
            if section.key == "abstract"
            and section.status == "generated"
        ),
        "",
    )

    keywords = next(
        (
            section.content_markdown
            for section in sections
            if section.key == "keywords"
            and section.status == "generated"
        ),
        "",
    )

    main_sections = [
        section.latex_code
        for section in sections
        if section.key not in {"abstract", "keywords"}
        and section.status == "generated"
        and section.latex_code
    ]

    bibtex = _build_bibtex(citations)

    abstract_body = abstract.strip()

    if abstract_body.startswith("\\section{Abstract}"):
        abstract_body = abstract_body.replace(
            "\\section{Abstract}",
            "",
            1,
        ).strip()

    keyword_text = _clean_text(keywords)

    if keyword_text.startswith("Keywords"):
        keyword_text = keyword_text.split(
            ":",
            1,
        )[-1].strip()

    return "\n".join(
        [
            "\\documentclass[12pt,a4paper]{article}",
            "",
            "\\usepackage[utf8]{inputenc}",
            "\\usepackage[T1]{fontenc}",
            "\\usepackage{geometry}",
            "\\usepackage{hyperref}",
            "\\usepackage{enumitem}",
            "\\usepackage{natbib}",
            "\\usepackage[hidelinks]{hyperref}",
            "",
            "\\geometry{margin=1in}",
            "",
            f"\\title{{{title}}}",
            "\\author{Author Name}",
            "\\date{\\today}",
            "",
            "\\begin{document}",
            "",
            "\\maketitle",
            "",
            "\\begin{abstract}",
            abstract_body or (
                "This workspace contains a proposed research "
                "study based on the selected literature corpus."
            ),
            "\\end{abstract}",
            "",
            (
                "\\noindent\\textbf{Keywords:} "
                f"{_latex_escape(keyword_text)}"
                if keyword_text
                else ""
            ),
            "",
            "\n\n".join(main_sections),
            "",
            "\\bibliographystyle{plain}",
            "\\bibliography{references}",
            "",
            "\\end{document}",
            "",
            "% The BibTeX entries are returned separately; save them as references.bib.",
        ]
    )


def _build_generation_prompt(
    workspace: Dict[str, Any],
    content_key: str,
    section_title: str,
    target_word_count: int,
    citation_style: str,
    instructions: str,
    papers: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
    purpose: str = "",
) -> str:
    idea = workspace.get("idea") or {}

    citation_lines = "\n".join(
        (
            f"- Internal citation [{paper['paper_id']}] "
            f"maps to LaTeX \\cite{{{paper['citation_key']}}}: "
            f"{paper['title']}"
        )
        for paper in papers
    )
    citation_lines = _clip_text(citation_lines, 2_400)

    citation_instruction = (
        "Use internal citations exactly as [paper_id]."
        if citation_style == "internal"
        else (
            "Use LaTeX citations exactly as "
            "\\cite{citation_key}."
        )
    )

    return f"""
Write one academic section for a proposed research paper.

SECTION KEY:
{content_key}

SECTION TITLE:
{section_title}

SECTION PURPOSE:
{purpose or 'Develop the requested section from the workspace evidence.'}

TARGET LENGTH:
Approximately {target_word_count} words.

WORKSPACE TITLE:
{_clip_text(workspace.get('title'), 300)}

WORKSPACE RESEARCH OBJECTIVE:
{_clip_text(workspace.get('research_objective'), 600) or 'Not specified'}

SELECTED RESEARCH IDEA:
Title: {_clip_text(idea.get('title'), 300)}
Problem statement: {_clip_text(idea.get('problem_statement'), 700)}
Hypothesis: {_clip_text(idea.get('hypothesis'), 400)}
Recommended methodology: {_clip_text(idea.get('recommended_methodology'), 500)}
Expected contribution: {_clip_text(idea.get('expected_contribution'), 500)}
Supporting idea paper IDs: {', '.join(idea.get('evidence_paper_ids') or []) or 'Not specified'}

USER INSTRUCTIONS:
{instructions.strip()[:MAX_PROMPT_INSTRUCTION_CHARS] or 'No additional instructions.'}

CITATION RULE:
{citation_instruction}

ALLOWED CITATIONS:
{citation_lines}

SELECTED PAPER METADATA AND EXTRACTIONS:
{_build_paper_context(papers)}

RETRIEVED EVIDENCE PASSAGES:
{_build_chunk_context(chunks) or 'No passage-level evidence was retrieved. Use only available metadata and explicitly use cautious language.'}

Write only the section content. Do not write a bibliography.
Do not use a Markdown code fence.
""".strip()


def _generation_warnings(
    papers: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
) -> List[str]:
    warnings: List[str] = []

    if not chunks:
        warnings.append(
            "No chunk-level passages were retrieved. "
            "The output is grounded primarily in stored paper "
            "metadata and extraction fields."
        )

    missing_extraction = [
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

    if missing_extraction:
        warnings.append(
            "Some selected papers have limited extracted fields: "
            + ", ".join(missing_extraction[:3])
            + "."
        )

    warnings.append(
        "Generated content is a proposed-study draft. Verify all "
        "claims, citations, research methods, LaTeX, and academic "
        "formatting before use."
    )

    return warnings


def _is_rate_limit_error(exc: Exception) -> bool:
    """Return whether a provider exception represents a temporary 429."""
    status_code = getattr(exc, "status_code", None)
    error_text = str(exc).lower()

    return (
        status_code == 429
        or "rate_limit" in error_text
        or "rate limit" in error_text
        or "tokens per minute" in error_text
        or "status code: 429" in error_text
    )


def _retry_delay_seconds(exc: Exception, attempt: int) -> float:
    """Use Retry-After when supplied, otherwise use a bounded backoff."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or {}
    retry_after = headers.get("retry-after") or headers.get("Retry-After")

    try:
        if retry_after is not None:
            return min(75.0, max(1.0, float(retry_after)))
    except (TypeError, ValueError):
        pass

    # Groq often reports the reset interval only in the error body. A
    # one-minute first wait clears the usual tokens-per-minute window.
    return min(75.0, 60.0 * (attempt + 1))


def _call_writer(
    prompt: str,
    max_tokens: int,
) -> str:
    if client is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "GROQ_API_KEY is missing. Add it to backend/.env "
                "and restart the backend."
            ),
        )

    completion = None
    last_rate_limit_error: Optional[Exception] = None

    # Full-paper generation is intentionally sequential. Retrying here means
    # a 429 pauses this job and lets the provider's token window reset, rather
    # than marking every later section as failed immediately.
    for attempt in range(3):
        try:
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
            break
        except Exception as exc:
            if not _is_rate_limit_error(exc):
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Workspace generation failed. "
                        f"Error type: {type(exc).__name__}. "
                        f"Details: {str(exc)}"
                    ),
                ) from exc

            last_rate_limit_error = exc
            if attempt < 2:
                time.sleep(_retry_delay_seconds(exc, attempt))

    if completion is None:
        raise HTTPException(
            status_code=429,
            detail=(
                "Generation is still rate-limited after automatic retries. "
                "Wait about a minute, then retry this section; no workspace "
                "data was lost."
            ),
        ) from last_rate_limit_error

    if not completion.choices:
        raise HTTPException(
            status_code=502,
            detail="Workspace generation returned no choices.",
        )

    content = (
        completion.choices[0].message.content
        or ""
    ).strip()

    if not content:
        raise HTTPException(
            status_code=502,
            detail="Workspace generation returned no content.",
        )

    return content


def _generate_single_section(
    workspace: Dict[str, Any],
    papers: List[Dict[str, Any]],
    content_key: str,
    section_title: str,
    target_word_count: int,
    citation_style: str,
    instructions: str,
    purpose: str = "",
) -> WorkspaceSectionResult:
    retrieval_key = (
        "methodology"
        if content_key == "proposed_methodology"
        else content_key
    )

    chunks = _retrieve_evidence(
        [paper["paper_id"] for paper in papers],
        retrieval_key,
    )

    citations, source_chunk_ids = _build_citations(
        papers,
        chunks,
    )

    prompt = _build_generation_prompt(
        workspace=workspace,
        content_key=content_key,
        section_title=section_title,
        target_word_count=target_word_count,
        citation_style=citation_style,
        instructions=instructions,
        papers=papers,
        chunks=chunks,
        purpose=purpose,
    )

    content_markdown = _call_writer(
        prompt=prompt,
        max_tokens=min(
            1400,
            max(450, int(target_word_count * 1.4)),
        ),
    )

    latex_code = _markdown_to_latex_section(
        markdown=content_markdown,
        title=section_title,
        citations=citations,
    )

    return WorkspaceSectionResult(
        key=content_key,
        title=section_title,
        content_markdown=content_markdown,
        latex_code=latex_code,
        citations=citations,
        warnings=_generation_warnings(papers, chunks),
        source_chunk_ids=source_chunk_ids,
        status="generated",
    )


def _default_outline(
    workspace: Dict[str, Any],
    papers: List[Dict[str, Any]],
    total_words: int,
) -> FullPaperOutline:
    idea = workspace.get("idea") or {}

    usable_total = max(1800, total_words)
    main_budget = int(usable_total * 0.84)

    sections: List[FullPaperSectionPlan] = []

    for item in FULL_PAPER_SECTION_ORDER:
        target = max(
            100,
            int(main_budget * item["weight"]),
        )

        sections.append(
            FullPaperSectionPlan(
                key=item["key"],
                title=item["title"],
                purpose=item["purpose"],
                target_word_count=target,
                evidence_paper_ids=[
                    paper["paper_id"]
                    for paper in papers
                ],
            )
        )

    keywords = []

    for paper in papers:
        keywords.extend(paper.get("keywords") or [])

    if not keywords:
        keywords = [
            word
            for word in re.findall(
                r"[A-Za-z][A-Za-z-]{3,}",
                _clean_text(idea.get("title")),
            )
        ]

    return FullPaperOutline(
        paper_title=(
            workspace.get("title")
            or _clean_text(idea.get("title"))
            or "ResearchOS Workspace Draft"
        ),
        abstract_target_word_count=max(
            120,
            min(300, int(usable_total * 0.08)),
        ),
        keywords=list(dict.fromkeys(keywords))[:8],
        sections=sections,
        model=settings.GROQ_MODEL,
    )


def _generate_outline(
    workspace: Dict[str, Any],
    papers: List[Dict[str, Any]],
    total_words: int,
    instructions: str,
) -> FullPaperOutline:
    default = _default_outline(
        workspace,
        papers,
        total_words,
    )

    if client is None:
        return default

    idea = workspace.get("idea") or {}
    available_ids = [
        paper["paper_id"]
        for paper in papers
    ]

    prompt = f"""
Create a concise shared outline for a proposed pre-experiment research paper.

WORKSPACE TITLE:
{_clip_text(workspace.get('title'), 300)}

WORKSPACE OBJECTIVE:
{_clip_text(workspace.get('research_objective'), 600) or 'Not specified'}

SELECTED IDEA:
Title: {_clip_text(idea.get('title'), 300)}
Problem statement: {_clip_text(idea.get('problem_statement'), 700)}
Hypothesis: {_clip_text(idea.get('hypothesis'), 400)}
Recommended methodology: {_clip_text(idea.get('recommended_methodology'), 500)}

TOTAL TARGET LENGTH:
Approximately {total_words} words.

USER INSTRUCTIONS:
{instructions.strip()[:MAX_PROMPT_INSTRUCTION_CHARS] or 'No additional instructions.'}

AVAILABLE PAPER IDS:
{', '.join(available_ids)}

PAPER EVIDENCE:
{_build_paper_context(papers)}

Return JSON only with exactly this shape:
{{
  "paper_title": "string",
  "keywords": ["string"],
  "sections": [
    {{
      "key": "introduction",
      "title": "Introduction",
      "purpose": "string",
      "target_word_count": 200,
      "evidence_paper_ids": ["allowed-paper-id"]
    }}
  ]
}}

Use exactly these section keys in this order:
introduction, research_problem, research_objectives,
research_questions, hypotheses, related_work,
proposed_methodology, proposed_framework,
experimental_design, evaluation_plan,
expected_contributions, limitations_and_scope, conclusion.

Do not include results or discussion sections because experiments have not been performed.
""".strip()

    try:
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            temperature=0.1,
            max_tokens=2200,
            messages=[
                {
                    "role": "system",
                    "content": OUTLINE_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        content = (
            completion.choices[0].message.content
            if completion.choices
            else ""
        )

        parsed = _parse_json(content)
    except Exception:
        return default

    if not parsed:
        return default

    valid_ids = set(available_ids)
    raw_sections = parsed.get("sections")

    if not isinstance(raw_sections, list):
        return default

    default_by_key = {
        section.key: section
        for section in default.sections
    }

    sections: List[FullPaperSectionPlan] = []

    for default_section in default.sections:
        match = next(
            (
                item
                for item in raw_sections
                if isinstance(item, dict)
                and item.get("key") == default_section.key
            ),
            None,
        )

        if not match:
            sections.append(default_section)
            continue

        evidence_ids = [
            str(value)
            for value in match.get(
                "evidence_paper_ids",
                [],
            )
            if str(value) in valid_ids
        ]

        sections.append(
            FullPaperSectionPlan(
                key=default_section.key,
                title=(
                    _clean_text(match.get("title"))
                    or default_section.title
                ),
                purpose=(
                    _clean_text(match.get("purpose"))
                    or default_section.purpose
                ),
                target_word_count=max(
                    80,
                    min(
                        1200,
                        int(
                            match.get(
                                "target_word_count",
                                default_section.target_word_count,
                            )
                        ),
                    ),
                ),
                evidence_paper_ids=(
                    evidence_ids
                    or default_section.evidence_paper_ids
                ),
            )
        )

    keywords = _safe_list(parsed.get("keywords"))

    return FullPaperOutline(
        paper_title=(
            _clean_text(parsed.get("paper_title"))
            or default.paper_title
        ),
        abstract_target_word_count=default.abstract_target_word_count,
        keywords=keywords[:8] or default.keywords,
        sections=sections,
        model=settings.GROQ_MODEL,
    )


def _generate_keywords_section(
    outline: FullPaperOutline,
    citations: List[WorkspaceCitation],
) -> WorkspaceSectionResult:
    content = (
        "Keywords: "
        + ", ".join(outline.keywords)
    )

    return WorkspaceSectionResult(
        key="keywords",
        title="Keywords",
        content_markdown=content,
        latex_code=(
            "\\noindent\\textbf{Keywords:} "
            + _latex_escape(", ".join(outline.keywords))
        ),
        citations=[],
        warnings=[],
        source_chunk_ids=[],
        status="generated",
    )


def _combine_markdown(
    workspace: Dict[str, Any],
    sections: List[WorkspaceSectionResult],
) -> str:
    title = workspace.get("title") or "ResearchOS Workspace Draft"

    parts = [f"# {title}"]

    abstract = next(
        (
            section.content_markdown
            for section in sections
            if section.key == "abstract"
            and section.status == "generated"
        ),
        "",
    )

    keywords = next(
        (
            section.content_markdown
            for section in sections
            if section.key == "keywords"
            and section.status == "generated"
        ),
        "",
    )

    if abstract:
        parts.extend(
            [
                "## Abstract",
                abstract,
            ]
        )

    if keywords:
        parts.append(keywords)

    section_number = 1

    for section in sections:
        if section.key in {"abstract", "keywords"}:
            continue

        if section.status == "generated":
            parts.extend(
                [
                    f"## {section_number}. {section.title}",
                    section.content_markdown,
                ]
            )
        else:
            parts.extend(
                [
                    f"## {section_number}. {section.title}",
                    (
                        "_This section was not generated. "
                        f"Reason: {section.error or 'Unknown error'}_"
                    ),
                ]
            )

        section_number += 1

    return "\n\n".join(parts)


def _combine_warnings(
    sections: List[WorkspaceSectionResult],
) -> List[str]:
    warnings: List[str] = []

    for section in sections:
        for warning in section.warnings:
            if warning not in warnings:
                warnings.append(warning)

        if section.status == "failed":
            failure = (
                f"Section '{section.title}' failed: "
                f"{section.error or 'Unknown generation error'}"
            )

            if failure not in warnings:
                warnings.append(failure)

    return warnings


def _combine_citations(
    sections: List[WorkspaceSectionResult],
) -> List[WorkspaceCitation]:
    citations: List[WorkspaceCitation] = []
    seen = set()

    for section in sections:
        for citation in section.citations:
            if citation.paper_id in seen:
                continue

            seen.add(citation.paper_id)
            citations.append(citation)

    return citations


def _combine_chunk_ids(
    sections: List[WorkspaceSectionResult],
) -> List[str]:
    values: List[str] = []

    for section in sections:
        values.extend(section.source_chunk_ids)

    return list(dict.fromkeys(values))


def _build_full_paper_prompt(
    workspace: Dict[str, Any],
    outline: FullPaperOutline,
    request: WorkspaceGenerateRequest,
    papers: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
) -> str:
    """Build one compact request for a complete short workspace draft."""
    idea = workspace.get("idea") or {}
    plans = [
        (
            "abstract",
            "Abstract",
            "Summarize the proposed problem, objective, methodology, and "
            "expected contribution without claiming results.",
            outline.abstract_target_word_count,
        ),
        *[
            (
                plan.key,
                plan.title,
                plan.purpose,
                plan.target_word_count,
            )
            for plan in outline.sections
        ],
    ]
    section_plan = "\n".join(
        (
            f"@@SECTION:{key}@@ | {title} | about {word_count} words | "
            f"{purpose}"
        )
        for key, title, purpose, word_count in plans
    )
    citation_lines = _clip_text(
        "\n".join(
            f"- [{paper['paper_id']}]: {paper['title']}"
            for paper in papers
        ),
        1_200,
    )

    return f"""
Write a concise, evidence-grounded proposed research-paper draft.

WORKSPACE:
Title: {_clip_text(workspace.get('title'), 220)}
Objective: {_clip_text(workspace.get('research_objective'), 420) or 'Not specified'}
Idea: {_clip_text(idea.get('title'), 220)}
Problem: {_clip_text(idea.get('problem_statement'), 420)}
Hypothesis: {_clip_text(idea.get('hypothesis'), 260)}
Method direction: {_clip_text(idea.get('recommended_methodology'), 320)}

USER INSTRUCTIONS:
{request.instructions.strip()[:MAX_PROMPT_INSTRUCTION_CHARS] or 'No additional instructions.'}

SECTION PLAN (write every item, in this order):
{section_plan}

ALLOWED INTERNAL CITATIONS:
{citation_lines}

PAPER METADATA AND EXTRACTIONS:
{_build_paper_context(papers)}

RETRIEVED EVIDENCE:
{_build_chunk_context(chunks) or 'No passage-level evidence was retrieved.'}

Output only the section bodies. Put each body immediately after its exact
@@SECTION:key@@ marker from the plan. Do not omit, rename, or add markers.
Use citations only as [paper_id]. Do not include a bibliography, Markdown
code fences, completed results, or unsupported claims.
""".strip()


def _parse_full_paper_sections(
    content: str,
    expected_keys: List[str],
) -> Dict[str, str]:
    marker = re.compile(r"^@@SECTION:([a-z_]+)@@[ \t]*", re.MULTILINE)
    matches = list(marker.finditer(content))
    parsed: Dict[str, str] = {}

    for index, match in enumerate(matches):
        key = match.group(1)
        if key not in expected_keys:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        body = content[match.end():end].strip()
        if body:
            parsed[key] = body

    return parsed


def _generate_full_paper_sections(
    workspace: Dict[str, Any],
    outline: FullPaperOutline,
    request: WorkspaceGenerateRequest,
    papers: List[Dict[str, Any]],
) -> List[WorkspaceSectionResult]:
    # A full-paper draft used to make fourteen nearly identical LLM calls.
    # One structured request is faster and stays well below the TPM limit.
    chunks = _retrieve_evidence(
        [paper["paper_id"] for paper in papers],
        "related_work",
    )
    citations, source_chunk_ids = _build_citations(papers, chunks)
    plans = [("abstract", "Abstract", outline.abstract_target_word_count)] + [
        (plan.key, plan.title, plan.target_word_count)
        for plan in outline.sections
    ]
    expected_keys = [key for key, _, _ in plans]
    content = _call_writer(
        _build_full_paper_prompt(workspace, outline, request, papers, chunks),
        max_tokens=min(3_500, max(1_200, int(request.target_word_count * 1.7))),
    )
    parsed = _parse_full_paper_sections(content, expected_keys)
    sections: List[WorkspaceSectionResult] = []

    for key, title, _ in plans:
        body = parsed.get(key, "")
        if not body:
            sections.append(
                WorkspaceSectionResult(
                    key=key,
                    title=title,
                    content_markdown="",
                    latex_code="",
                    status="failed",
                    error="The generation response did not contain this section.",
                )
            )
            continue

        sections.append(
            WorkspaceSectionResult(
                key=key,
                title=title,
                content_markdown=body,
                latex_code=_markdown_to_latex_section(body, title, citations),
                citations=citations,
                warnings=_generation_warnings(papers, chunks),
                source_chunk_ids=source_chunk_ids,
                status="generated",
            )
        )

    sections.insert(1, _generate_keywords_section(outline, citations))
    return sections


def _generate_full_paper(
    workspace_id: str,
    workspace: Dict[str, Any],
    request: WorkspaceGenerateRequest,
    papers: List[Dict[str, Any]],
) -> WorkspaceGenerationResponse:
    # The deterministic outline is already evidence-aware and avoids a
    # separate planning request before the section writers begin. This removes
    # one provider round trip and makes full-paper generation more responsive.
    outline = _default_outline(
        workspace=workspace,
        papers=papers,
        total_words=request.target_word_count,
    )

    all_citations, _ = _build_citations(papers, [])
    sections = _generate_full_paper_sections(
        workspace=workspace,
        outline=outline,
        request=request,
        papers=papers,
    )

    citations = _combine_citations(sections)

    if not citations:
        citations = all_citations

    full_markdown = _combine_markdown(
        workspace,
        sections,
    )

    full_latex = ""

    if request.generate_latex:
        full_latex = _full_paper_latex(
            workspace,
            sections,
            citations,
        )

    return WorkspaceGenerationResponse(
        workspace_id=workspace_id,
        generation_mode="full_paper",
        content_type=None,
        title=outline.paper_title,
        content_markdown=full_markdown,
        latex_code=full_latex,
        citations=citations,
        warnings=_combine_warnings(sections),
        source_chunk_ids=_combine_chunk_ids(sections),
        model=settings.GROQ_MODEL,
        outline=outline,
        sections=sections,
        full_paper_markdown=full_markdown,
        full_paper_latex=full_latex,
        bibtex=(
            _build_bibtex(citations)
            if request.generate_bibtex
            else ""
        ),
    )


def generate_workspace_content(
    workspace_id: str,
    request: WorkspaceGenerateRequest,
) -> WorkspaceGenerationResponse:
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

    if request.generation_mode == "full_paper":
        return _generate_full_paper(
            workspace_id=workspace_id,
            workspace=workspace,
            request=request,
            papers=papers,
        )

    if not request.content_type:
        raise HTTPException(
            status_code=400,
            detail=(
                "content_type is required when generation_mode "
                "is 'section'."
            ),
        )

    title = CONTENT_TITLES[request.content_type]

    section = _generate_single_section(
        workspace=workspace,
        papers=papers,
        content_key=request.content_type,
        section_title=title,
        target_word_count=request.target_word_count,
        citation_style=request.citation_style,
        instructions=request.instructions,
    )

    return WorkspaceGenerationResponse(
        workspace_id=workspace_id,
        generation_mode="section",
        content_type=request.content_type,
        title=title,
        content_markdown=section.content_markdown,
        latex_code=(
            section.latex_code
            if request.generate_latex
            else ""
        ),
        citations=section.citations,
        warnings=section.warnings,
        source_chunk_ids=section.source_chunk_ids,
        model=settings.GROQ_MODEL,
        sections=[section],
    )


def create_workspace_version(
    workspace_id: str,
    payload: WorkspaceVersionCreate,
) -> WorkspaceVersionResponse:
    _get_workspace_document(workspace_id)

    now = datetime.utcnow()

    latest = workspace_versions_collection.find_one(
        {"workspace_id": workspace_id},
        sort=[("version", -1)],
    )

    version_number = (
        int(latest.get("version", 0)) + 1
        if latest
        else 1
    )

    document = {
        "workspace_id": workspace_id,
        "generation_mode": payload.generation_mode,
        "content_type": payload.content_type,
        "content_markdown": payload.content_markdown,
        "latex_code": payload.latex_code,
        "citations": [
            citation.model_dump()
            for citation in payload.citations
        ],
        "warnings": payload.warnings,
        "source_chunk_ids": payload.source_chunk_ids,
        "outline": (
            payload.outline.model_dump()
            if payload.outline
            else None
        ),
        "sections": [
            section.model_dump()
            for section in payload.sections
        ],
        "full_paper_markdown": payload.full_paper_markdown,
        "full_paper_latex": payload.full_paper_latex,
        "bibtex": payload.bibtex,
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
            )
        },
        {
            "$set": {
                "updated_at": now
            }
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
        {"workspace_id": workspace_id}
    ).sort("version", -1)

    return [
        WorkspaceVersionResponse(
            **_serialize_version(document)
        )
        for document in documents
    ]
