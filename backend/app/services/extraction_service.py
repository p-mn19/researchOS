import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


from bson import ObjectId
from fastapi import HTTPException
from groq import Groq


from app.config import settings
from app.db import (
    extractions_collection,
    papers_collection,
)


FIELDS = [
    "objective",
    "methodology",
    "dataset",
    "evaluation_metric",
    "limitations",
    "future_work",
    "research_gap",
    "findings",
    "keywords",
]


client = None


if settings.GROQ_API_KEY.strip():
    client = Groq(
        api_key=settings.GROQ_API_KEY.strip(),
        base_url="https://api.groq.com",
        timeout=60.0,
        max_retries=2,
    )


SYSTEM_PROMPT = """
You extract structured information from an academic paper.

Use only the supplied paper text.
Do not invent facts.
If the paper does not provide information for a field,
return an empty string.

Return valid JSON only.
Do not use Markdown fences.
Do not add explanations outside the JSON.

The response must contain exactly the requested keys.
Each value must be a concise factual summary of no more than 80 words.
Do not copy long passages from the paper.
Preserve dataset names, sample sizes, algorithms,
metrics, percentages, and important limitations.
For 'keywords', return a JSON array of 5–10 short terms.
""".strip()


def _clean_value(value: Any) -> Any:
    if value is None:
        return ""

    if isinstance(value, list):
        cleaned = [_clean_value(item) for item in value]
        return [item for item in cleaned if item not in ("", [], {})]

    if isinstance(value, dict):
        cleaned = {}
        for k, v in value.items():
            cv = _clean_value(v)
            if cv not in ("", [], {}):
                cleaned[k] = cv
        return cleaned

    text = " ".join(str(value).split()).strip()
    return text if text else ""


def _empty_result(
    fields: List[str],
) -> Dict[str, Any]:
    return {
        field: ([] if field == "keywords" else "")
        for field in fields
    }


def _normalise_result(
    value: Any,
    fields: List[str],
) -> Dict[str, Any]:
    result = _empty_result(fields)

    if not isinstance(value, dict):
        return result

    for field in fields:
        raw = value.get(field)
        if field == "keywords":
            kw = _clean_value(raw)
            result[field] = kw if isinstance(kw, list) else []
        else:
            result[field] = _clean_value(raw)

    return result


def _parse_json(
    content: str,
    fields: List[str],
) -> Dict[str, Any]:
    content = content.strip()

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
        return _normalise_result(
            json.loads(content),
            fields,
        )
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start < 0 or end <= start:
            return _empty_result(fields)
        try:
            parsed = json.loads(
                content[start:end + 1]
            )
        except json.JSONDecodeError:
            return _empty_result(fields)
        return _normalise_result(
            parsed,
            fields,
        )


def _get_paper_text(
    paper: Dict[str, Any],
) -> str:
    for field in [
        "raw_text",
        "text",
        "content",
        "full_text",
    ]:
        value = paper.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()

    pages = paper.get("pages") or []
    page_texts = []

    for page in pages:
        if isinstance(page, dict):
            value = page.get("text") or ""
        else:
            value = str(page or "")

        if value.strip():
            page_texts.append(value.strip())

    return "\n\n".join(page_texts).strip()


def _find_section(
    text: str,
    headings: List[str],
    max_chars: int = 7000,
) -> str:
    heading_group = "|".join(
        sorted(
            (
                re.escape(heading)
                for heading in headings
            ),
            key=len,
            reverse=True,
        )
    )

    start_pattern = re.compile(
        rf"(?im)^[ \t]*"
        rf"(?:\d+(?:\.\d+)*[.)]?[ \t]*)?"
        rf"(?:{heading_group})"
        rf"[ \t]*[:.\-]?[ \t]*$"
    )

    start_match = start_pattern.search(text)
    if not start_match:
        return ""

    remaining = text[
        start_match.end():
    ]

    all_headings = [
        "abstract",
        "introduction",
        "background",
        "objective",
        "aim",
        "purpose",
        "methodology",
        "methods",
        "approach",
        "dataset",
        "data set",
        "database",
        "evaluation",
        "metrics",
        "results",
        "discussion",
        "limitations",
        "limitation",
        "future work",
        "future directions",
        "research gap",
        "gap",
        "findings",
        "results and findings",
        "conclusion",
        "references",
        "bibliography",
    ]

    end_group = "|".join(
        sorted(
            (
                re.escape(heading)
                for heading in all_headings
            ),
            key=len,
            reverse=True,
        )
    )

    end_pattern = re.compile(
        rf"(?im)^[ \t]*"
        rf"(?:\d+(?:\.\d+)*[.)]?[ \t]*)?"
        rf"(?:{end_group})"
        rf"[ \t]*[:.\-]?[ \t]*$"
    )

    end_match = end_pattern.search(
        remaining
    )

    if end_match:
        remaining = remaining[
            :end_match.start()
        ]

    return remaining[:max_chars].strip()


def _build_relevant_text(
    text: str,
    fields: List[str],
) -> str:
    parts = []

    beginning = text[:10000]
    parts.append(
        "BEGINNING OF PAPER\n"
        + beginning
    )

    if "limitations" in fields:
        limitations = _find_section(
            text,
            [
                "limitations",
                "limitation",
                "constraints",
            ],
        )
        if limitations:
            parts.append(
                "LIMITATIONS SECTION\n"
                + limitations
            )

    if "future_work" in fields:
        future_work = _find_section(
            text,
            [
                "future work",
                "future directions",
                "further work",
            ],
        )
        if future_work:
            parts.append(
                "FUTURE WORK SECTION\n"
                + future_work
            )

    if "research_gap" in fields:
        gap = _find_section(
            text,
            [
                "research gap",
                "gap",
                "open problem",
                "open challenge",
            ],
        )
        if gap:
            parts.append(
                "RESEARCH GAP SECTION\n"
                + gap
            )

    if "findings" in fields:
        findings = _find_section(
            text,
            [
                "findings",
                "results and findings",
                "key results",
            ],
        )
        if findings:
            parts.append(
                "FINDINGS SECTION\n"
                + findings
            )

    return "\n\n".join(parts)


def _extract_group(
    text: str,
    fields: List[str],
) -> Dict[str, Any]:
    if client is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "GROQ_API_KEY is missing. "
                "Add it to backend/.env and "
                "restart the backend."
            ),
        )

    field_list = "\n".join(
        f"- {field}"
        for field in fields
    )

    context = _build_relevant_text(
        text,
        fields,
    )

    prompt = f"""
Extract only these fields:

{field_list}

Paper text:
{context}

Return exactly one JSON object using only
the requested field names.
Use an empty string for missing information.
For 'keywords', return a JSON array of 5–10 short terms.
Keep every non-empty field to 80 words or fewer,
then ensure the JSON object is closed.
""".strip()

    try:
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            temperature=0,
            max_tokens=1800,
            response_format={
                "type": "json_object",
            },
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
            detail=(
                "Structured extraction failed: "
                f"{str(exc)}"
            ),
        ) from exc

    if not completion.choices:
        return _empty_result(fields)

    content = (
        completion.choices[0]
        .message.content
        or "{}"
    )

    return _parse_json(
        content,
        fields,
    )


def _extract_all_fields(
    text: str,
) -> Dict[str, Any]:
    result = _empty_result(FIELDS)

    groups = [
        [
            "objective",
            "methodology",
            "dataset",
            "evaluation_metric",
        ],
        [
            "limitations",
            "future_work",
            "research_gap",
            "findings",
        ],
        ["keywords"],
    ]

    for fields in groups:
        partial = _extract_group(
            text,
            fields,
        )
        for field in fields:
            value = partial.get(field, "")
            if value not in ("", [], {}):
                result[field] = value

    return result


def extract_paper_content(
    paper_id: str,
    paper: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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

    text = _get_paper_text(paper)

    if not text:
        raise HTTPException(
            status_code=400,
            detail=(
                "Paper has no parsed text. "
                "Run parsing before extraction."
            ),
        )

    fields = _extract_all_fields(text)

    extraction_document = {
        "paper_id": paper_id,
        **fields,
        "updated_at": datetime.utcnow(),
    }

    extractions_collection.update_one(
        {"paper_id": paper_id},
        {
            "$set": extraction_document
        },
        upsert=True,
    )

    papers_collection.update_one(
        {"_id": object_id},
        {
            "$set": {
                "status": "extracted",
                "extracted_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                # Also mirror key fields on the paper doc
                "methodology": fields.get("methodology"),
                "dataset": fields.get("dataset"),
                "limitations": fields.get("limitations"),
                "research_gap": fields.get("research_gap"),
                "findings": fields.get("findings"),
                "keywords": fields.get("keywords", []),
                "future_work": fields.get("future_work"),
                "objective": fields.get("objective"),
            }
        },
    )

    return fields


extract_fields_for_paper = (
    extract_paper_content
)