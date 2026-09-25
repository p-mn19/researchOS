from __future__ import annotations

import json
import random
import re
import time
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import HTTPException

from app.config import settings
from app.db import (
    chunks_collection,
    extractions_collection,
    papers_collection,
)
from app.services.groq_client import (
    get_groq_client,
    has_groq_api_keys,
)


# ============================================================
# REVIEW CONFIGURATION
# ============================================================

REVIEW_DIMENSIONS = [
    {
        "id": "clarity",
        "title": "Problem Clarity & Literature Coverage",
        "description": (
            "Assesses whether the paper clearly defines the research problem, "
            "motivation, objectives, and relationship to relevant literature."
        ),
    },
    {
        "id": "novelty",
        "title": "Novelty / Contribution",
        "description": (
            "Assesses whether the paper clearly states its contribution and "
            "distinguishes it from related work. This does not independently "
            "verify global novelty."
        ),
    },
    {
        "id": "methodology",
        "title": "Method Justification & Completeness",
        "description": (
            "Assesses whether the methods are appropriate, justified, sufficiently "
            "described, and reproducible from the supplied evidence."
        ),
    },
    {
        "id": "evidence",
        "title": "Evidence & Results",
        "description": (
            "Assesses whether the datasets, experiments, metrics, comparisons, "
            "and reported results support the paper's claims."
        ),
    },
    {
        "id": "limitations",
        "title": "Limitations & Scope",
        "description": (
            "Assesses whether the paper acknowledges assumptions, limitations, "
            "scope boundaries, risks, and future work."
        ),
    },
]

CONCERN_LEVELS = {
    "None",
    "Moderate",
    "Major",
    "Critical",
}

CONFIDENCE_LEVELS = {
    "Low",
    "Medium",
    "High",
}

SCORE_GUIDE = {
    "1-2": "Very weak: little or no sufficient evidence was supplied for this dimension.",
    "3-4": "Weak: major weaknesses or missing evidence materially affect the assessment.",
    "5-6": "Mixed: some useful evidence is present, but important gaps or uncertainties remain.",
    "7-8": "Generally solid: the paper is reasonably supported, with some areas to strengthen.",
    "9-10": "Strong: the supplied evidence is clear, specific, and strongly supports this dimension.",
}

CONCERN_GUIDE = {
    "None": "No significant concern was identified from the supplied evidence.",
    "Moderate": "A meaningful issue or uncertainty should be clarified or strengthened.",
    "Major": "An important weakness or missing evidence materially affects the assessment.",
    "Critical": "A fundamental issue exists, or essential information is unavailable for responsible assessment.",
}

CONFIDENCE_GUIDE = {
    "Low": "The supplied evidence is limited, ambiguous, or incomplete.",
    "Medium": "The evidence reasonably supports the assessment, but uncertainty remains.",
    "High": "The supplied paper evidence clearly supports the assessment.",
}

# Keep one review request comfortably below a low TPM allowance.
MAX_REVIEW_CHUNKS = 6
MAX_CHUNK_CHARS = 900
MAX_REVIEW_CONTEXT_CHARS = 11_000
MAX_REVIEW_OUTPUT_TOKENS = 1_600
MAX_REVIEW_RETRIES = 3


# ============================================================
# HELPERS
# ============================================================


def _text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item is not None)

    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)

    return " ".join(str(value).split()).strip()


def _clean_text(value: Any) -> str:
    return " ".join(_text(value).split()).strip()


def _clip_text(value: Any, limit: int) -> str:
    text = _clean_text(value)

    if len(text) <= limit:
        return text

    clipped = text[:limit]

    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]

    return f"{clipped}..."


def _safe_list(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []

    if not isinstance(value, list):
        return []

    result: List[str] = []

    for item in value:
        cleaned = _clean_text(item)
        if cleaned:
            result.append(cleaned)

    return result


def _score(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0

    numeric = max(1, min(10, round(numeric)))
    return f"{numeric}/10"


def _score_number(value: Any) -> int:
    try:
        numeric = int(round(float(value)))
    except (TypeError, ValueError):
        numeric = 1

    return max(1, min(10, numeric))


def _score_explanation(score: int) -> str:
    if score <= 2:
        return SCORE_GUIDE["1-2"]

    if score <= 4:
        return SCORE_GUIDE["3-4"]

    if score <= 6:
        return SCORE_GUIDE["5-6"]

    if score <= 8:
        return SCORE_GUIDE["7-8"]

    return SCORE_GUIDE["9-10"]


def _normalise_enum(value: Any, allowed: set[str], fallback: str) -> str:
    value = _clean_text(value)

    if not value:
        return fallback

    if value in allowed:
        return value

    for item in allowed:
        if item.lower() == value.lower():
            return item

    return fallback


def _is_rate_limit_or_too_large_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    text = str(exc).lower()

    return (
        status_code in {413, 429}
        or "rate limit" in text
        or "rate_limit" in text
        or "tokens per minute" in text
        or "tpm" in text
        or "request too large" in text
        or "rate_limit_exceeded" in text
        or "status code: 413" in text
        or "status code: 429" in text
    )


def _retry_delay(attempt: int) -> float:
    return min(20.0, 2.0**attempt) + random.uniform(0.0, 0.75)


# ============================================================
# PAPER LOOKUP
# ============================================================


def _find_paper(paper_id: str) -> Optional[dict]:
    paper_id = str(paper_id or "").strip()

    if not paper_id:
        return None

    if ObjectId.is_valid(paper_id):
        paper = papers_collection.find_one({"_id": ObjectId(paper_id)})
        if paper:
            return paper

    if paper_id.isdigit():
        paper = papers_collection.find_one({"_id": int(paper_id)})
        if paper:
            return paper

    return papers_collection.find_one({"id": paper_id})


def _find_extraction(paper_id: str, paper: dict) -> dict:
    candidates = [paper_id, str(paper.get("_id", ""))]
    candidates = [value for value in candidates if value]

    if not candidates:
        return {}

    extraction = extractions_collection.find_one(
        {"paper_id": {"$in": candidates}},
    )

    return extraction or {}


# ============================================================
# CHUNK RETRIEVAL
# ============================================================


def _get_paper_chunks(paper_id: str) -> List[dict]:
    """Retrieve a small, stable sample of paper chunks."""
    paper_id = str(paper_id or "").strip()

    if not paper_id:
        return []

    return list(
        chunks_collection.find(
            {"paper_id": paper_id},
            {
                "_id": 0,
                "text": 1,
                "page": 1,
                "page_number": 1,
                "section_title": 1,
            },
        )
        .sort([("page", 1), ("page_number", 1)])
        .limit(MAX_REVIEW_CHUNKS),
    )


# ============================================================
# REVIEW CONTEXT
# ============================================================


def _build_review_context(
    paper: dict,
    extraction: dict,
    chunks: List[dict],
) -> str:
    title = (
        _clean_text(paper.get("title"))
        or _clean_text(paper.get("filename"))
        or "Untitled paper"
    )

    abstract = _clip_text(paper.get("abstract"), 1_500)
    objective = _clip_text(extraction.get("objective") or paper.get("objective"), 650)
    methodology = _clip_text(
        extraction.get("methodology") or paper.get("methodology"),
        850,
    )
    dataset = _clip_text(extraction.get("dataset") or paper.get("dataset"), 400)
    metrics = _clip_text(
        extraction.get("evaluation_metric")
        or extraction.get("metrics")
        or paper.get("evaluation_metric"),
        400,
    )
    findings = _clip_text(extraction.get("findings") or paper.get("findings"), 850)
    limitations = _clip_text(
        extraction.get("limitations") or paper.get("limitations"),
        650,
    )
    future_work = _clip_text(
        extraction.get("future_work") or paper.get("future_work"),
        500,
    )
    research_gap = _clip_text(
        extraction.get("research_gap") or paper.get("research_gap"),
        500,
    )
    keywords = _safe_list(extraction.get("keywords") or paper.get("keywords"))

    parts = [
        "=== PAPER METADATA ===",
        f"Title: {title}",
        "",
        "=== ABSTRACT ===",
        abstract or "[Not available]",
        "",
        "=== STRUCTURED EXTRACTION ===",
        f"Objective: {objective or '[Not available]'}",
        f"Methodology: {methodology or '[Not available]'}",
        f"Dataset: {dataset or '[Not available]'}",
        f"Evaluation Metrics: {metrics or '[Not available]'}",
        f"Findings: {findings or '[Not available]'}",
        f"Limitations: {limitations or '[Not available]'}",
        f"Future Work: {future_work or '[Not available]'}",
        f"Research Gap: {research_gap or '[Not available]'}",
        f"Keywords: {', '.join(keywords[:12]) or '[Not available]'}",
        "",
        "=== SELECTED SOURCE PASSAGES ===",
    ]

    used_chars = len("\n".join(parts))
    included_passages = 0

    for index, chunk in enumerate(chunks, start=1):
        text = _clip_text(chunk.get("text"), MAX_CHUNK_CHARS)

        if not text:
            continue

        page = chunk.get("page") or chunk.get("page_number") or "?"
        section = _clean_text(chunk.get("section_title"))
        location = f"Page {page}" if not section else f"Page {page}, Section: {section}"
        block = f"\n--- Passage {index} ({location}) ---\n{text}"

        if used_chars + len(block) > MAX_REVIEW_CONTEXT_CHARS:
            break

        parts.append(block)
        used_chars += len(block)
        included_passages += 1

    if included_passages == 0:
        parts.append("[No parsed paper passages were available.]")

    return "\n".join(parts)


# ============================================================
# REVIEW PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are the ResearchOS academic review engine.

Analyse the supplied paper evidence and return a compact, structured
academic review. Use only the supplied information.

Rules:
1. Do not invent facts, citations, datasets, results, or missing details.
2. Distinguish “not reported” from “poor quality”.
3. Do not make a publication decision.
4. Novelty cannot be proven from one paper alone; assess only whether
   the contribution is clearly stated and differentiated in the evidence.
5. Return valid JSON only. Do not use Markdown or code fences.
6. Keep the complete response concise. Each evidence and suggestion field
   should be one or two sentences.

Evaluate exactly these dimensions:
- clarity: Problem Clarity & Literature Coverage
- novelty: Novelty / Contribution
- methodology: Method Justification & Completeness
- evidence: Evidence & Results
- limitations: Limitations & Scope

For each dimension provide:
- score: 1 to 10
- concern: None, Moderate, Major, or Critical
- confidence: Low, Medium, or High
- evidence: concise, grounded rationale
- suggestion: one actionable improvement

Return exactly this JSON shape:
{
  "overall_score": 7.5,
  "overall_assessment": "One concise paragraph.",
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "missing_information": ["...", "..."],
  "dimensions": [
    {
      "id": "clarity",
      "title": "Problem Clarity & Literature Coverage",
      "score": 8,
      "concern": "Moderate",
      "confidence": "High",
      "evidence": "...",
      "suggestion": "..."
    }
  ]
}

The dimensions array must contain exactly five objects with IDs:
clarity, novelty, methodology, evidence, limitations.
""".strip()


# ============================================================
# JSON EXTRACTION
# ============================================================


def _parse_json(content: str) -> Dict[str, Any]:
    content = (content or "").strip()

    if not content:
        return {}

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?", "", content, flags=re.IGNORECASE)
        content = re.sub(r"```$", "", content).strip()

    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    start = content.find("{")
    end = content.rfind("}")

    if start < 0 or end <= start:
        return {}

    try:
        parsed = json.loads(content[start : end + 1])
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


# ============================================================
# REVIEW NORMALISATION
# ============================================================


def _normalise_dimension(
    raw: Dict[str, Any],
    expected: Dict[str, str],
) -> Dict[str, Any]:
    numeric_score = _score_number(raw.get("score"))
    concern = _normalise_enum(
        raw.get("concern"),
        CONCERN_LEVELS,
        "Moderate",
    )
    confidence = _normalise_enum(
        raw.get("confidence"),
        CONFIDENCE_LEVELS,
        "Medium",
    )

    return {
        "id": expected["id"],
        "title": expected["title"],
        "description": expected["description"],
        "score": f"{numeric_score}/10",
        "scoreExplanation": _score_explanation(numeric_score),
        "concern": concern,
        "concernExplanation": CONCERN_GUIDE[concern],
        "confidence": confidence,
        "confidenceExplanation": CONFIDENCE_GUIDE[confidence],
        "evidence": (
            _clean_text(raw.get("evidence"))
            or "The supplied paper evidence was insufficient to provide a detailed assessment."
        ),
        "suggestion": (
            _clean_text(raw.get("suggestion"))
            or "Provide additional evidence or clarification for this dimension."
        ),
    }


def _normalise_review(
    raw: Dict[str, Any],
    paper_id: str,
    title: str,
) -> Dict[str, Any]:
    raw_dimensions = raw.get("dimensions")

    if not isinstance(raw_dimensions, list):
        raw_dimensions = []

    by_id: Dict[str, Dict[str, Any]] = {}

    for item in raw_dimensions:
        if not isinstance(item, dict):
            continue

        item_id = _clean_text(item.get("id")).lower()
        if item_id:
            by_id[item_id] = item

    dimensions = [
        _normalise_dimension(by_id.get(expected["id"], {}), expected)
        for expected in REVIEW_DIMENSIONS
    ]

    scores = [
        _score_number(dimension["score"].replace("/10", ""))
        for dimension in dimensions
    ]
    average_score = sum(scores) / len(scores) if scores else 0

    try:
        overall_score = float(raw.get("overall_score"))
        if not 1 <= overall_score <= 10:
            raise ValueError
    except (TypeError, ValueError):
        overall_score = round(average_score, 1)

    overall_assessment = _clean_text(raw.get("overall_assessment")) or (
        "The review was generated from the evidence available in the supplied paper."
    )

    return {
        "paperId": paper_id,
        "paperTitle": title,
        "overallScore": f"{overall_score:.1f}/10",
        "overallAssessment": overall_assessment,
        "summary": overall_assessment,
        "strengths": _safe_list(raw.get("strengths")),
        "weaknesses": _safe_list(raw.get("weaknesses")),
        "missingInformation": _safe_list(raw.get("missing_information")),
        "dimensions": dimensions,
        "guidance": {
            "scoreRanges": SCORE_GUIDE,
            "concerns": CONCERN_GUIDE,
            "confidence": CONFIDENCE_GUIDE,
            "note": (
                "Not reported does not automatically mean poor quality. "
                "A lower confidence or concern level can reflect limited or ambiguous supplied evidence."
            ),
        },
        "model": getattr(settings, "GROQ_MODEL", ""),
    }


# ============================================================
# MODEL CALL
# ============================================================


def _call_review_model(context: str) -> Dict[str, Any]:
    if not has_groq_api_keys():
        raise HTTPException(
            status_code=503,
            detail="No Groq API key is configured. Review generation requires Groq.",
        )

    model = getattr(settings, "GROQ_MODEL", "openai/gpt-oss-20b")
    last_error: Optional[Exception] = None

    for attempt in range(MAX_REVIEW_RETRIES):
        client = get_groq_client(timeout=90.0, max_retries=1)

        if client is None:
            raise HTTPException(
                status_code=503,
                detail="No Groq API key is configured. Review generation requires Groq.",
            )

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": "Analyse this paper evidence:\n\n" + context,
                    },
                ],
                temperature=0.1,
                max_tokens=MAX_REVIEW_OUTPUT_TOKENS,
            )

            content = ""
            if response.choices:
                content = response.choices[0].message.content or ""

            parsed = _parse_json(content)

            if not parsed:
                raise HTTPException(
                    status_code=502,
                    detail="Review model returned invalid JSON.",
                )

            return parsed

        except HTTPException:
            raise

        except Exception as exc:
            last_error = exc

            if _is_rate_limit_or_too_large_error(exc) and attempt < MAX_REVIEW_RETRIES - 1:
                time.sleep(_retry_delay(attempt))
                continue

            if _is_rate_limit_or_too_large_error(exc):
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Review generation is temporarily rate-limited. Wait about a minute "
                        "and try again. The review request has been reduced to a compact "
                        "evidence context."
                    ),
                ) from exc

            raise HTTPException(
                status_code=502,
                detail=f"Review model request failed: {str(exc)}",
            ) from exc

    raise HTTPException(
        status_code=429,
        detail=(
            "Review generation is temporarily rate-limited. "
            f"Last error: {str(last_error) if last_error else 'Unknown error'}"
        ),
    )


# ============================================================
# PUBLIC SERVICE
# ============================================================


def generate_review(paper_id: str) -> Dict[str, Any]:
    paper_id = str(paper_id or "").strip()

    if not paper_id:
        raise HTTPException(status_code=400, detail="Paper ID is required.")

    paper = _find_paper(paper_id)

    if not paper:
        raise HTTPException(
            status_code=404,
            detail=f"Paper not found for ID: {paper_id}",
        )

    extraction = _find_extraction(paper_id, paper)
    chunks = _get_paper_chunks(paper_id)
    title = (
        _clean_text(paper.get("title"))
        or _clean_text(paper.get("filename"))
        or "Untitled paper"
    )
    context = _build_review_context(
        paper=paper,
        extraction=extraction,
        chunks=chunks,
    )
    raw_review = _call_review_model(context)

    return _normalise_review(
        raw=raw_review,
        paper_id=paper_id,
        title=title,
    )