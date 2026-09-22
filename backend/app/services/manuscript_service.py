import json
import re
from typing import Any, Dict, List

from bson import ObjectId
from fastapi import HTTPException
from app.config import settings
from app.services.groq_client import get_groq_client, has_groq_api_keys
from app.db import extractions_collection, papers_collection
from app.schemas.manuscript import (
    CitationSource,
    DraftSectionRequest,
    DraftSectionResponse,
    SectionPlanRequest,
    SectionPlanResponse,
    SentencePlan,
)
from app.services.search_service import semantic_search


PLAN_SYSTEM_PROMPT = """
You are ResearchOS Module 9: a citation-grounded academic manuscript planning assistant.

Use only the supplied paper information.

Create a structured sentence plan for either:
- related_work
- methodology

Rules:
1. Do not invent methods, datasets, results, authors, papers, or citations.
2. Every planned claim must include citation_paper_ids using only supplied paper IDs.
3. For a methodology section, distinguish existing evidence from a proposed methodology.
4. For related work, synthesize papers by themes rather than one-paper-per-paragraph summaries.
5. Return valid JSON only, without Markdown.
6. Use exactly the JSON shape requested.
""".strip()


DRAFT_SYSTEM_PROMPT = """
You are ResearchOS Module 9: a citation-grounded academic manuscript drafting assistant.

Write a scholarly manuscript section using only the supplied evidence.

Rules:
1. Do not invent facts, numeric results, methods, datasets, or citations.
2. Cite every evidence-based claim with the supplied citation format: [paper_id].
3. Only cite paper IDs that appear in the supplied source list.
4. If evidence is insufficient, explicitly say that evidence is limited instead of filling gaps.
5. Do not claim a method was performed unless the supplied plan labels it as proposed.
6. Return Markdown text only. Do not wrap it in a code block.
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

        if start == -1 or end <= start:
            return {}

        try:
            parsed = json.loads(content[start:end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


def _paper_query(paper_ids: List[str]) -> Dict[str, Any]:
    object_ids = [
        ObjectId(paper_id)
        for paper_id in paper_ids
        if ObjectId.is_valid(paper_id)
    ]

    conditions = []

    if object_ids:
        conditions.append({"_id": {"$in": object_ids}})

    if paper_ids:
        conditions.append({"id": {"$in": paper_ids}})

    return {"$or": conditions} if conditions else {"_id": {"$in": []}}


def _get_papers_with_extractions(
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
            detail="No selected papers were found.",
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
        str(item.get("paper_id")): item
        for item in extractions
        if item.get("paper_id")
    }

    records = []

    for paper_id, paper in paper_map.items():
        extraction = extraction_map.get(paper_id, {})

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
                "findings": _clean_text(
                    extraction.get("findings")
                    or paper.get("findings")
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
            }
        )

    return records


def _build_metadata_context(
    papers: List[Dict[str, Any]],
) -> str:
    blocks = []

    for paper in papers:
        blocks.append(
            "\n".join(
                [
                    f"PAPER ID: {paper['paper_id']}",
                    f"TITLE: {paper['title']}",
                    f"AUTHORS: {', '.join(paper['authors']) or 'Not available'}",
                    f"YEAR: {paper['year'] or 'Not available'}",
                    f"ABSTRACT: {paper['abstract'] or 'Not available'}",
                    f"OBJECTIVE: {paper['objective'] or 'Not available'}",
                    f"METHODOLOGY: {paper['methodology'] or 'Not available'}",
                    f"DATASET: {paper['dataset'] or 'Not available'}",
                    f"FINDINGS: {paper['findings'] or 'Not available'}",
                    f"LIMITATIONS: {paper['limitations'] or 'Not available'}",
                    f"FUTURE WORK: {paper['future_work'] or 'Not available'}",
                    f"RESEARCH GAP: {paper['research_gap'] or 'Not available'}",
                ]
            )
        )

    return "\n\n---\n\n".join(blocks)


def _section_title(section_type: str) -> str:
    return (
        "Related Work"
        if section_type == "related_work"
        else "Methodology"
    )


def _safe_sentence_plan(
    items: Any,
    valid_paper_ids: List[str],
) -> List[SentencePlan]:
    if not isinstance(items, list):
        return []

    valid_ids = set(valid_paper_ids)
    plans = []

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue

        citation_ids = [
            str(paper_id)
            for paper_id in item.get(
                "citation_paper_ids",
                [],
            )
            if str(paper_id) in valid_ids
        ]

        purpose = _clean_text(item.get("purpose"))
        claim = _clean_text(item.get("claim"))

        if not purpose or not claim:
            continue

        plans.append(
            SentencePlan(
                sentence_number=int(
                    item.get("sentence_number")
                    or index
                ),
                purpose=purpose,
                claim=claim,
                citation_paper_ids=citation_ids,
            )
        )

    return plans


def _completion_content(completion: Any) -> str:
    if not completion.choices:
        return ""

    return completion.choices[0].message.content or ""


def _citation_sources(
    papers: List[Dict[str, Any]],
) -> List[CitationSource]:
    return [
        CitationSource(
            paper_id=paper["paper_id"],
            title=paper["title"],
            authors=paper["authors"],
            year=paper["year"],
        )
        for paper in papers
    ]


def generate_section_plan(
    request: SectionPlanRequest,
) -> SectionPlanResponse:
    if not has_groq_api_keys():
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY or GROQ_API_KEYS is missing.",
        )

    paper_ids = list(
        dict.fromkeys(
            str(paper_id).strip()
            for paper_id in request.paper_ids
            if str(paper_id).strip()
        )
    )

    papers = _get_papers_with_extractions(paper_ids)
    paper_context = _build_metadata_context(papers)

    topic = (
        request.research_topic.strip()
        if request.research_topic
        else "Not specified"
    )

    prompt = f"""
Create a sentence plan for a {request.section_type} section.

Research topic: {topic}
Target length: approximately {request.target_word_count} words.

Return exactly this JSON object:
{{
  "objective": "...",
  "sentence_plan": [
    {{
      "sentence_number": 1,
      "purpose": "...",
      "claim": "...",
      "citation_paper_ids": ["paper_id"]
    }}
  ]
}}

PAPER EVIDENCE:
{paper_context}
""".strip()

    try:
        client = get_groq_client()
        assert client is not None
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            temperature=0.25,
            max_tokens=2200,
            messages=[
                {
                    "role": "system",
                    "content": PLAN_SYSTEM_PROMPT,
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
            detail=f"Section-plan generation failed: {str(exc)}",
        ) from exc

    valid_paper_ids = [paper["paper_id"] for paper in papers]
    content = _completion_content(completion)
    parsed = _parse_json(content)
    sentence_plan = _safe_sentence_plan(
        parsed.get("sentence_plan"),
        valid_paper_ids,
    )

    # Some models occasionally return prose or incomplete JSON despite the
    # prompt. Ask once for a corrected response before showing an empty plan.
    if not sentence_plan:
        correction_prompt = """
Your previous response could not be used as a sentence plan.
Return the requested plan now as one valid JSON object only. Do not include
Markdown, commentary, or code fences. Include a non-empty `sentence_plan`
array whose items each contain `sentence_number`, `purpose`, `claim`, and
`citation_paper_ids` using only the supplied paper IDs.
""".strip()

        try:
            retry_client = get_groq_client()
            assert retry_client is not None
            retry_completion = retry_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                temperature=0.1,
                max_tokens=2200,
                messages=[
                    {
                        "role": "system",
                        "content": PLAN_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                    {
                        "role": "assistant",
                        "content": content,
                    },
                    {
                        "role": "user",
                        "content": correction_prompt,
                    },
                ],
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Section-plan retry failed: {str(exc)}",
            ) from exc

        parsed = _parse_json(_completion_content(retry_completion))
        sentence_plan = _safe_sentence_plan(
            parsed.get("sentence_plan"),
            valid_paper_ids,
        )

    return SectionPlanResponse(
        section_type=request.section_type,
        section_title=_section_title(request.section_type),
        objective=_clean_text(parsed.get("objective")) or (
            f"Develop a citation-grounded "
            f"{_section_title(request.section_type)} section."
        ),
        sentence_plan=sentence_plan,
        recommended_sources=_citation_sources(papers),
        model=settings.GROQ_MODEL,
    )


def _retrieve_evidence(
    request: DraftSectionRequest,
) -> List[Dict[str, Any]]:
    if request.section_type == "related_work":
        query = (
            request.research_topic
            or "methods approaches findings limitations related work"
        )
    else:
        query = (
            request.research_topic
            or "methodology methods dataset evaluation approach"
        )

    return semantic_search(
        query=query,
        paper_ids=request.paper_ids,
        top_k=min(20, max(8, len(request.paper_ids) * 4)),
    )


def _build_chunk_context(
    chunks: List[Dict[str, Any]],
) -> str:
    blocks = []

    for chunk in chunks:
        paper_id = str(chunk.get("paper_id") or "")
        title = str(chunk.get("paper_title") or "Untitled paper")
        section = str(chunk.get("section_title") or "Unknown section")
        page = chunk.get("page")
        text = _clean_text(chunk.get("text"))

        if not paper_id or not text:
            continue

        location = (
            f", page {page}"
            if page is not None
            else ""
        )

        blocks.append(
            "\n".join(
                [
                    f"SOURCE PAPER ID: {paper_id}",
                    f"TITLE: {title}",
                    f"LOCATION: {section}{location}",
                    f"EVIDENCE: {text}",
                ]
            )
        )

    return "\n\n---\n\n".join(blocks)


def _build_plan_context(
    sentence_plan: List[SentencePlan],
) -> str:
    if not sentence_plan:
        return "No explicit sentence plan was supplied."

    return "\n".join(
        [
            (
                f"{item.sentence_number}. "
                f"Purpose: {item.purpose} | "
                f"Claim: {item.claim} | "
                f"Allowed citations: {', '.join(item.citation_paper_ids) or 'none'}"
            )
            for item in sentence_plan
        ]
    )


def _plan_as_editable_draft(
    request: DraftSectionRequest,
) -> str:
    """Create an honest editable fallback when a model returns no draft."""
    title = _section_title(request.section_type)
    sentence_plan = request.sentence_plan

    if not sentence_plan:
        return (
            f"# {title}\n\n"
            "No draft text was returned. Create a section plan first, then "
            "generate the draft again."
        )

    words_per_item = max(
        1,
        round(request.target_word_count / len(sentence_plan)),
    )
    blocks = [
        f"# {title}",
        (
            "*Editable outline generated from the sentence plan. Expand and "
            f"revise each item toward the {request.target_word_count}-word target.*"
        ),
    ]

    for item in sentence_plan:
        citations = " ".join(
            f"[{paper_id}]"
            for paper_id in item.citation_paper_ids
        )
        blocks.append(
            "\n".join(
                [
                    (
                        f"## Sentence {item.sentence_number} "
                        f"(~{words_per_item} words)"
                    ),
                    item.claim,
                    f"*Purpose: {item.purpose}*",
                    citations,
                ]
            ).strip()
        )

    return "\n\n".join(blocks)


def generate_draft_section(
    request: DraftSectionRequest,
) -> DraftSectionResponse:
    if not has_groq_api_keys():
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY or GROQ_API_KEYS is missing.",
        )

    paper_ids = list(
        dict.fromkeys(
            str(paper_id).strip()
            for paper_id in request.paper_ids
            if str(paper_id).strip()
        )
    )

    papers = _get_papers_with_extractions(paper_ids)
    chunks = _retrieve_evidence(request)

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail=(
                "No searchable evidence was found. "
                "Parse and index the selected papers before drafting."
            ),
        )

    metadata_context = _build_metadata_context(papers)
    chunk_context = _build_chunk_context(chunks)
    plan_context = _build_plan_context(request.sentence_plan)

    topic = (
        request.research_topic.strip()
        if request.research_topic
        else "the selected research topic"
    )

    prompt = f"""
Write the '{_section_title(request.section_type)}' section.

Research topic: {topic}
Target length: approximately {request.target_word_count} words.

Follow this controllable sentence plan:
{plan_context}

Use this paper metadata:
{metadata_context}

Use this retrieved passage evidence:
{chunk_context}

Use inline citations exactly as [paper_id].
Only use paper IDs from the evidence above.
""".strip()

    try:
        client = get_groq_client()
        assert client is not None
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            temperature=0.2,
            max_tokens=min(
                3500,
                max(1000, request.target_word_count * 2),
            ),
            messages=[
                {
                    "role": "system",
                    "content": DRAFT_SYSTEM_PROMPT,
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
            detail=f"Draft generation failed: {str(exc)}",
        ) from exc

    markdown = (
        completion.choices[0].message.content.strip()
        if completion.choices
        and completion.choices[0].message.content
        else ""
    )

    if not markdown:
        markdown = _plan_as_editable_draft(request)

    citations = _citation_sources(papers)

    return DraftSectionResponse(
        section_type=request.section_type,
        section_title=_section_title(request.section_type),
        markdown=markdown,
        citations=citations,
        model=settings.GROQ_MODEL,
    )
