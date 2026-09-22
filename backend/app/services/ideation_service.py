import json
import re
from typing import Any, Dict, List

from bson import ObjectId
from fastapi import HTTPException
from app.config import settings
from app.services.groq_client import get_groq_client, has_groq_api_keys
from app.db import extractions_collection, papers_collection
from app.schemas.ideation import (
    EvidencePaper,
    IdeationRequest,
    IdeationResponse,
    ResearchIdea,
)


SYSTEM_PROMPT = """
You are ResearchOS Module 8: an academic research-gap and ideation assistant.

Your task is to analyze only the supplied evidence from a collection of academic papers.

Rules:
1. Use only the supplied paper evidence.
2. Do not claim that a research gap is proven or globally novel.
3. Describe outputs as candidate research gaps and candidate research ideas.
4. Every research idea must reference one or more supplied paper IDs in evidence_paper_ids.
5. Do not invent papers, paper IDs, datasets, methods, metrics, findings, or citations.
6. Research hypotheses must be testable.
7. Recommended methodologies must be realistic and connected to limitations or future-work evidence.
8. Return valid JSON only. No Markdown, no explanations outside JSON.

Return exactly this JSON shape:
{
  "recurring_limitations": ["..."],
  "research_gaps": ["..."],
  "recommended_methodologies": ["..."],
  "ideas": [
    {
      "title": "...",
      "problem_statement": "...",
      "hypothesis": "...",
      "recommended_methodology": "...",
      "expected_contribution": "...",
      "evidence_paper_ids": ["..."]
    }
  ]
}
""".strip()


NO_LIMITATION_EXTRACTED = (
    "No limitation was extracted from the available paper text; "
    "review the source paper for study constraints."
)

NO_FUTURE_WORK_EXTRACTED = (
    "No future-work recommendation was extracted from the available paper text; "
    "review the source paper for proposed next steps."
)


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

    conditions: List[Dict[str, Any]] = []

    if object_ids:
        conditions.append({"_id": {"$in": object_ids}})

    if paper_ids:
        conditions.append({"id": {"$in": paper_ids}})

    if not conditions:
        return {"_id": {"$in": []}}

    return {"$or": conditions}


def _get_selected_papers(
    paper_ids: List[str],
) -> List[Dict[str, Any]]:
    documents = list(
        papers_collection.find(
            _paper_query(paper_ids)
        )
    )

    if not documents:
        raise HTTPException(
            status_code=404,
            detail="No selected papers were found.",
        )

    paper_map = {
        str(paper["_id"]): paper
        for paper in documents
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
                "keywords": _clean_text(
                    extraction.get("keywords")
                    or paper.get("keywords")
                ),
            }
        )

    return records


def _build_evidence_context(
    papers: List[Dict[str, Any]],
) -> str:
    blocks = []

    for paper in papers:
        blocks.append(
            "\n".join(
                [
                    f"PAPER ID: {paper['paper_id']}",
                    f"TITLE: {paper['title']}",
                    f"ABSTRACT: {paper['abstract'] or 'Not available'}",
                    f"OBJECTIVE: {paper['objective'] or 'Not available'}",
                    f"METHODOLOGY: {paper['methodology'] or 'Not available'}",
                    f"DATASET: {paper['dataset'] or 'Not available'}",
                    f"LIMITATIONS: {paper['limitations'] or 'Not available'}",
                    f"FUTURE WORK: {paper['future_work'] or 'Not available'}",
                    f"RESEARCH GAP: {paper['research_gap'] or 'Not available'}",
                    f"FINDINGS: {paper['findings'] or 'Not available'}",
                    f"KEYWORDS: {paper['keywords'] or 'Not available'}",
                ]
            )
        )

    return "\n\n---\n\n".join(blocks)


def _safe_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []

    return [
        _clean_text(item)
        for item in value
        if _clean_text(item)
    ]


def _safe_ideas(
    value: Any,
    valid_paper_ids: List[str],
) -> List[ResearchIdea]:
    if not isinstance(value, list):
        return []

    valid_id_set = set(valid_paper_ids)
    ideas: List[ResearchIdea] = []

    for item in value:
        if not isinstance(item, dict):
            continue

        evidence_ids = [
            str(paper_id)
            for paper_id in item.get(
                "evidence_paper_ids",
                [],
            )
            if str(paper_id) in valid_id_set
        ]

        title = _clean_text(item.get("title"))
        problem_statement = _clean_text(
            item.get("problem_statement")
        )
        hypothesis = _clean_text(item.get("hypothesis"))
        methodology = _clean_text(
            item.get("recommended_methodology")
        )
        contribution = _clean_text(
            item.get("expected_contribution")
        )

        if not title or not problem_statement:
            continue

        ideas.append(
            ResearchIdea(
                title=title,
                problem_statement=problem_statement,
                hypothesis=hypothesis or (
                    "A testable hypothesis should be refined "
                    "from the selected corpus evidence."
                ),
                recommended_methodology=methodology or (
                    "A methodology should be selected after "
                    "reviewing the referenced evidence."
                ),
                expected_contribution=contribution or (
                    "A potential contribution should be validated "
                    "against the selected literature."
                ),
                evidence_paper_ids=evidence_ids,
            )
        )

    return ideas


def generate_ideation(
    request: IdeationRequest,
) -> IdeationResponse:
    if not has_groq_api_keys():
        raise HTTPException(
            status_code=500,
            detail=(
                "GROQ_API_KEY or GROQ_API_KEYS is missing. Add it to backend/.env "
                "and restart the backend."
            ),
        )

    paper_ids = list(
        dict.fromkeys(
            str(paper_id).strip()
            for paper_id in request.paper_ids
            if str(paper_id).strip()
        )
    )

    if not paper_ids:
        raise HTTPException(
            status_code=400,
            detail="At least one paper ID is required.",
        )

    papers = _get_selected_papers(paper_ids)
    evidence_context = _build_evidence_context(papers)

    topic_instruction = (
        f"\nUser research direction: {request.topic.strip()}"
        if request.topic and request.topic.strip()
        else ""
    )

    prompt = f"""
Analyze the following selected paper corpus.
Generate exactly {request.idea_count} candidate research ideas.
{topic_instruction}

PAPER EVIDENCE:
{evidence_context}
""".strip()

    try:
        client = get_groq_client()
        assert client is not None
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            temperature=0.35,
            max_tokens=2800,
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
            detail=f"Ideation generation failed: {str(exc)}",
        ) from exc

    content = (
        completion.choices[0].message.content
        if completion.choices and completion.choices[0].message.content
        else "{}"
    )

    parsed = _parse_json(content)
    valid_paper_ids = [paper["paper_id"] for paper in papers]

    evidence_papers = [
        EvidencePaper(
            paper_id=paper["paper_id"],
            title=paper["title"],
            limitation=(
                paper["limitations"]
                or NO_LIMITATION_EXTRACTED
            ),
            future_work=(
                paper["future_work"]
                or NO_FUTURE_WORK_EXTRACTED
            ),
            research_gap=paper["research_gap"] or None,
            methodology=paper["methodology"] or None,
        )
        for paper in papers
    ]

    return IdeationResponse(
        corpus_size=len(papers),
        topic=request.topic,
        recurring_limitations=_safe_list(
            parsed.get("recurring_limitations")
        ),
        research_gaps=_safe_list(
            parsed.get("research_gaps")
        ),
        recommended_methodologies=_safe_list(
            parsed.get("recommended_methodologies")
        ),
        ideas=_safe_ideas(
            parsed.get("ideas"),
            valid_paper_ids,
        ),
        evidence_papers=evidence_papers,
        model=settings.GROQ_MODEL,
    )
