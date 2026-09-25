import json
import re
import threading
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import HTTPException
from groq import Groq

from app.config import settings
from app.db import (
    chunks_collection,
    extractions_collection,
    papers_collection,
)


# ============================================================
# REVIEW CONFIGURATION
# ============================================================

REVIEW_DIMENSIONS = [
    {
        "id": "clarity",
        "title": "Problem Clarity & Literature Coverage",
    },
    {
        "id": "novelty",
        "title": "Novelty / Contribution",
    },
    {
        "id": "methodology",
        "title": "Method Justification & Completeness",
    },
    {
        "id": "evidence",
        "title": "Evidence & Results",
    },
    {
        "id": "limitations",
        "title": "Limitations & Scope",
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


# ============================================================
# GROQ CLIENTS
# ============================================================

# The config supports multiple Groq keys through:
#
# settings.groq_api_keys
#
# This property automatically handles:
# - GROQ_API_KEYS
# - GROQ_API_KEY fallback
# - duplicate keys
#
# We create one Groq client per configured key.

groq_clients: List[Groq] = []

for api_key in settings.groq_api_keys:
    groq_clients.append(
        Groq(
            api_key=api_key,
            timeout=90.0,
            max_retries=2,
        )
    )


# Round-robin state.
_groq_index = 0
_groq_lock = threading.Lock()


def _get_groq_client() -> Optional[Groq]:
    """
    Return the next configured Groq client using round-robin rotation.

    Example with 5 keys:

        request 1 -> key 1
        request 2 -> key 2
        request 3 -> key 3
        request 4 -> key 4
        request 5 -> key 5
        request 6 -> key 1
        ...

    The lock protects the rotation counter when multiple
    FastAPI requests are processed concurrently.
    """

    global _groq_index

    if not groq_clients:
        return None

    with _groq_lock:
        client = groq_clients[
            _groq_index % len(groq_clients)
        ]

        _groq_index = (
            _groq_index + 1
        ) % len(groq_clients)

        return client


# ============================================================
# HELPERS
# ============================================================

def _text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(
            str(item)
            for item in value
            if item is not None
        )

    if isinstance(value, dict):
        return json.dumps(
            value,
            ensure_ascii=False,
        )

    return " ".join(
        str(value).split()
    ).strip()


def _clean_text(value: Any) -> str:
    return " ".join(
        _text(value).split()
    ).strip()


def _safe_list(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return []

        return [value]

    if not isinstance(value, list):
        return []

    result = []

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

    numeric = max(
        1,
        min(
            10,
            round(numeric),
        ),
    )

    return f"{numeric}/10"


def _score_number(value: Any) -> int:
    try:
        numeric = int(
            round(
                float(value)
            )
        )
    except (TypeError, ValueError):
        numeric = 1

    return max(
        1,
        min(10, numeric),
    )


def _normalise_enum(
    value: Any,
    allowed: set,
    fallback: str,
) -> str:
    value = _clean_text(value)

    if not value:
        return fallback

    # Exact match first.
    if value in allowed:
        return value

    # Case-insensitive match.
    for item in allowed:
        if item.lower() == value.lower():
            return item

    return fallback


# ============================================================
# PAPER LOOKUP
# ============================================================

def _find_paper(
    paper_id: str,
) -> Optional[dict]:
    paper_id = str(
        paper_id or ""
    ).strip()

    if not paper_id:
        return None

    if ObjectId.is_valid(paper_id):
        paper = papers_collection.find_one(
            {
                "_id": ObjectId(paper_id)
            }
        )

        if paper:
            return paper

    if paper_id.isdigit():
        numeric_id = int(paper_id)

        paper = papers_collection.find_one(
            {
                "_id": numeric_id
            }
        )

        if paper:
            return paper

        paper = papers_collection.find_one(
            {
                "id": paper_id
            }
        )

        if paper:
            return paper

    return None


def _find_extraction(
    paper_id: str,
    paper: dict,
) -> dict:

    candidates = [
        paper_id,
        str(
            paper.get("_id", "")
        ),
    ]

    candidates = [
        value
        for value in candidates
        if value
    ]

    if not candidates:
        return {}

    extraction = extractions_collection.find_one(
        {
            "paper_id": {
                "$in": candidates
            }
        }
    )

    return extraction or {}


# ============================================================
# CHUNK RETRIEVAL
# ============================================================

def _get_paper_chunks(
    paper_id: str,
) -> List[dict]:

    paper_id = str(
        paper_id or ""
    ).strip()

    if not paper_id:
        return []

    chunks = list(
        chunks_collection.find(
            {
                "paper_id": paper_id
            },
            {
                "_id": 0,
                "text": 1,
                "page": 1,
                "page_number": 1,
                "section_title": 1,
            },
        ).sort(
            [
                ("page", 1),
                ("page_number", 1),
            ]
        )
    )

    return chunks


# ============================================================
# REVIEW CONTEXT
# ============================================================

def _build_review_context(
    paper: dict,
    extraction: dict,
    chunks: List[dict],
) -> str:

    title = (
        _clean_text(
            paper.get("title")
        )
        or _clean_text(
            paper.get("filename")
        )
        or "Untitled paper"
    )

    abstract = _clean_text(
        paper.get("abstract")
    )

    objective = _clean_text(
        extraction.get("objective")
        or paper.get("objective")
    )

    methodology = _clean_text(
        extraction.get("methodology")
        or paper.get("methodology")
    )

    dataset = _clean_text(
        extraction.get("dataset")
        or paper.get("dataset")
    )

    metrics = _clean_text(
        extraction.get("evaluation_metric")
        or extraction.get("metrics")
        or paper.get("evaluation_metric")
    )

    findings = _clean_text(
        extraction.get("findings")
        or paper.get("findings")
    )

    limitations = _clean_text(
        extraction.get("limitations")
        or paper.get("limitations")
    )

    future_work = _clean_text(
        extraction.get("future_work")
        or paper.get("future_work")
    )

    research_gap = _clean_text(
        extraction.get("research_gap")
        or paper.get("research_gap")
    )

    keywords = _safe_list(
        extraction.get("keywords")
        or paper.get("keywords")
    )

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
        f"Keywords: {', '.join(keywords) or '[Not available]'}",
        "",
        "=== SOURCE PAPER CHUNKS ===",
    ]

    if chunks:
        for index, chunk in enumerate(
            chunks,
            start=1,
        ):
            text = _clean_text(
                chunk.get("text")
            )

            if not text:
                continue

            page = (
                chunk.get("page")
                or chunk.get("page_number")
                or "?"
            )

            section = _clean_text(
                chunk.get("section_title")
            )

            location = (
                f"Page {page}"
                if not section
                else f"Page {page}, Section: {section}"
            )

            parts.append(
                f"\n--- Chunk {index} ({location}) ---\n"
                f"{text}"
            )
    else:
        parts.append(
            "[No parsed paper chunks were found.]"
        )

    return "\n".join(parts)


# ============================================================
# REVIEW PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are the ResearchOS academic review engine.

Your task is to analyse an academic research paper and produce a
structured review.

IMPORTANT:

Use ONLY the supplied paper information.

Do not invent facts.
Do not assume missing information exists.
Do not treat typical academic conventions as evidence.
Do not fabricate citations.
Do not claim that a paper is novel merely because its methodology
looks different.
Do not make a publication decision.

The review is decision support for the researcher, NOT a real
peer-review decision.

Evaluate exactly these five dimensions:

1. Problem Clarity & Literature Coverage
2. Novelty / Contribution
3. Method Justification & Completeness
4. Evidence & Results
5. Limitations & Scope

For every dimension:

- score from 1 to 10
- assign a concern level:
  None
  Moderate
  Major
  Critical
- provide evidence grounded in the supplied paper
- provide one actionable suggestion
- provide confidence:
  Low
  Medium
  High

Interpret concern levels as follows:

None:
The supplied evidence does not reveal a significant concern for
this dimension.

Moderate:
There is a meaningful issue, uncertainty, or area that should be
clarified or strengthened.

Major:
There is an important weakness, missing evidence, or methodological
issue that materially affects the assessment.

Critical:
The supplied evidence reveals a fundamental problem or there is
not enough essential information to responsibly assess a key part
of the dimension.

IMPORTANT:
Missing information should NOT automatically receive Critical.
Distinguish between "not reported" and "poor quality".

Novelty:
Novelty cannot be proven from this paper alone. Assess whether the
paper clearly identifies its contribution and differentiates itself
from related work based only on supplied evidence.

Literature coverage:
Do not assume that the literature review is comprehensive simply
because an abstract exists.

Methodology:
Consider whether the method is sufficiently described, justified,
reproducible, and appropriate for the stated objective.

Evidence & Results:
Consider whether experiments, metrics, comparisons, results, and
interpretation provide sufficient evidence for the stated claims.

Limitations & Scope:
Consider whether limitations, assumptions, scope, and future work
are explicitly discussed and whether the conclusions remain within
the evidence.

Return valid JSON only.

Do not use Markdown fences.

Return exactly this structure:

{
  "overall_score": 7.5,
  "overall_assessment": "...",
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "missing_information": ["...", "..."],
  "dimensions": [
    {
      "id": "clarity",
      "title": "Problem Clarity & Literature Coverage",
      "score": 8,
      "concern": "None",
      "confidence": "High",
      "evidence": "...",
      "suggestion": "..."
    }
  ]
}

The dimensions array MUST contain exactly five items using the IDs:

clarity
novelty
methodology
evidence
limitations

Keep evidence concise but specific.

When possible, mention concrete details such as datasets,
algorithms, sample sizes, metrics, experiments, or reported
limitations.

Do not quote long passages.
""".strip()


# ============================================================
# JSON EXTRACTION
# ============================================================

def _parse_json(
    content: str,
) -> Dict[str, Any]:

    content = (
        content or ""
    ).strip()

    if not content:
        return {}

    # Remove Markdown fences if the model ignores the instruction.
    if content.startswith("```"):
        content = re.sub(
            r"^```(?:json)?",
            "",
            content,
            flags=re.IGNORECASE,
        )

        content = re.sub(
            r"```$",
            "",
            content,
        ).strip()

    try:
        parsed = json.loads(
            content
        )

        return (
            parsed
            if isinstance(parsed, dict)
            else {}
        )

    except json.JSONDecodeError:
        pass

    # Try extracting the JSON object.
    start = content.find("{")
    end = content.rfind("}")

    if start < 0 or end <= start:
        return {}

    try:
        parsed = json.loads(
            content[
                start:end + 1
            ]
        )

        return (
            parsed
            if isinstance(parsed, dict)
            else {}
        )

    except json.JSONDecodeError:
        return {}


# ============================================================
# REVIEW NORMALISATION
# ============================================================

def _normalise_dimension(
    raw: Dict[str, Any],
    expected: Dict[str, str],
) -> Dict[str, Any]:

    return {
        "id": expected["id"],
        "title": expected["title"],
        "score": _score(
            raw.get("score")
        ),
        "concern": _normalise_enum(
            raw.get("concern"),
            CONCERN_LEVELS,
            "Moderate",
        ),
        "confidence": _normalise_enum(
            raw.get("confidence"),
            CONFIDENCE_LEVELS,
            "Medium",
        ),
        "evidence": (
            _clean_text(
                raw.get("evidence")
            )
            or (
                "The supplied paper evidence was insufficient "
                "to provide a detailed assessment."
            )
        ),
        "suggestion": (
            _clean_text(
                raw.get("suggestion")
            )
            or (
                "Provide additional evidence or clarification "
                "for this dimension."
            )
        ),
    }


def _normalise_review(
    raw: Dict[str, Any],
    paper_id: str,
    title: str,
) -> Dict[str, Any]:

    raw_dimensions = raw.get(
        "dimensions"
    )

    if not isinstance(
        raw_dimensions,
        list,
    ):
        raw_dimensions = []

    by_id = {}

    for item in raw_dimensions:
        if not isinstance(
            item,
            dict,
        ):
            continue

        item_id = _clean_text(
            item.get("id")
        ).lower()

        if item_id:
            by_id[item_id] = item

    dimensions = []

    for expected in REVIEW_DIMENSIONS:
        raw_dimension = by_id.get(
            expected["id"],
            {},
        )

        dimensions.append(
            _normalise_dimension(
                raw_dimension,
                expected,
            )
        )

    scores = [
        _score_number(
            dimension["score"]
            .replace("/10", "")
        )
        for dimension in dimensions
    ]

    average_score = (
        sum(scores) / len(scores)
        if scores
        else 0
    )

    llm_overall_score = raw.get(
        "overall_score"
    )

    try:
        overall_score = float(
            llm_overall_score
        )

        if not 1 <= overall_score <= 10:
            raise ValueError

    except (
        TypeError,
        ValueError,
    ):
        overall_score = round(
            average_score,
            1,
        )

    overall_assessment = (
        _clean_text(
            raw.get(
                "overall_assessment"
            )
        )
        or (
            "The review was generated from the evidence available "
            "in the supplied paper."
        )
    )

    strengths = _safe_list(
        raw.get("strengths")
    )

    weaknesses = _safe_list(
        raw.get("weaknesses")
    )

    missing_information = _safe_list(
        raw.get("missing_information")
    )

    return {
        "paperId": paper_id,
        "paperTitle": title,
        "overallScore": (
            f"{overall_score:.1f}/10"
        ),
        "overallAssessment": overall_assessment,
        "summary": overall_assessment,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "missingInformation": missing_information,
        "dimensions": dimensions,
        "model": getattr(
            settings,
            "GROQ_MODEL",
            "",
        ),
    }


# ============================================================
# MODEL CALL
# ============================================================

def _call_review_model(
    context: str,
) -> Dict[str, Any]:

    client = _get_groq_client()

    if client is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "No Groq API key is configured. "
                "Review generation requires Groq."
            ),
        )

    model = getattr(
        settings,
        "GROQ_MODEL",
        "openai/gpt-oss-20b",
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        "Analyse the following paper.\n\n"
                        + context
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=5000,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Review model request failed: "
                f"{str(exc)}"
            ),
        ) from exc

    content = ""

    if response.choices:
        content = (
            response.choices[0]
            .message
            .content
            or ""
        )

    parsed = _parse_json(
        content
    )

    if not parsed:
        raise HTTPException(
            status_code=502,
            detail=(
                "Review model returned invalid JSON."
            ),
        )

    return parsed


# ============================================================
# PUBLIC SERVICE
# ============================================================

def generate_review(
    paper_id: str,
) -> Dict[str, Any]:

    paper_id = str(
        paper_id or ""
    ).strip()

    if not paper_id:
        raise HTTPException(
            status_code=400,
            detail="Paper ID is required.",
        )

    paper = _find_paper(
        paper_id
    )

    if not paper:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Paper not found for ID: "
                f"{paper_id}"
            ),
        )

    extraction = _find_extraction(
        paper_id,
        paper,
    )

    chunks = _get_paper_chunks(
        paper_id
    )

    title = (
        _clean_text(
            paper.get("title")
        )
        or _clean_text(
            paper.get("filename")
        )
        or "Untitled paper"
    )

    context = _build_review_context(
        paper=paper,
        extraction=extraction,
        chunks=chunks,
    )

    raw_review = _call_review_model(
        context
    )

    return _normalise_review(
        raw=raw_review,
        paper_id=paper_id,
        title=title,
    )