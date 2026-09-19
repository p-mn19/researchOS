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


# =========================================================
# FIELDS
# =========================================================

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


# =========================================================
# GROQ CLIENT
# =========================================================

client = None

if settings.GROQ_API_KEY.strip():
    client = Groq(
        api_key=settings.GROQ_API_KEY.strip(),
        base_url="https://api.groq.com",
        timeout=60.0,
        max_retries=2,
    )


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You extract structured information from an academic research paper.

STRICT RULES:

1. Use ONLY the supplied paper text.
2. Do NOT use outside knowledge.
3. Do NOT invent facts.
4. Preserve exact technical terminology.
5. Preserve exact dataset names.
6. Preserve exact sample counts and numerical values.
7. Preserve algorithms, models, preprocessing methods,
   evaluation metrics, percentages, thresholds, and
   experimental settings when present.
8. Do not replace specific information with generic descriptions.
9. Do not make unsupported assumptions.
10. Keep each non-empty text field concise and factual.
11. For future_work, include ONLY future work explicitly stated
    or clearly described by the authors.
12. Do NOT infer future work from limitations.
13. For research_gap, include only a gap directly supported
    by the paper.
14. If a field is genuinely unsupported, return an empty string.
15. For keywords, return 5–10 specific technical terms.
16. Return valid JSON only.
17. Do not use Markdown fences.
18. Return exactly the requested keys.
""".strip()


# =========================================================
# HELPERS
# =========================================================

def _clean_value(value: Any) -> Any:

    if value is None:
        return ""

    if isinstance(value, list):

        cleaned = [
            _clean_value(item)
            for item in value
        ]

        return [
            item
            for item in cleaned
            if item not in ("", [], {})
        ]

    if isinstance(value, dict):

        cleaned = {}

        for key, item in value.items():

            cleaned_value = _clean_value(item)

            if cleaned_value not in ("", [], {}):

                cleaned[key] = cleaned_value

        return cleaned

    text = " ".join(
        str(value).split()
    ).strip()

    return text if text else ""


def _empty_result(
    fields: List[str],
) -> Dict[str, Any]:

    return {
        field: (
            []
            if field == "keywords"
            else ""
        )
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

            cleaned = _clean_value(raw)

            if isinstance(cleaned, list):

                result[field] = [
                    str(item).strip()
                    for item in cleaned
                    if str(item).strip()
                ]

            else:

                result[field] = []

        else:

            result[field] = _clean_value(raw)

    return result


def _parse_json(
    content: str,
    fields: List[str],
) -> Dict[str, Any]:

    content = (
        content or ""
    ).strip()

    if not content:

        return _empty_result(fields)

    # Remove Markdown fences if the model accidentally adds them.
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

    # Normal JSON parsing.
    try:

        parsed = json.loads(content)

        return _normalise_result(
            parsed,
            fields,
        )

    except json.JSONDecodeError:

        pass

    # Try extracting the JSON object from surrounding text.
    start = content.find("{")
    end = content.rfind("}")

    if start >= 0 and end > start:

        try:

            parsed = json.loads(
                content[
                    start:end + 1
                ]
            )

            return _normalise_result(
                parsed,
                fields,
            )

        except json.JSONDecodeError:

            pass

    return _empty_result(fields)


# =========================================================
# PAPER TEXT
# =========================================================

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

        if (
            isinstance(value, str)
            and value.strip()
        ):

            return value.strip()

    pages = paper.get("pages") or []

    page_texts = []

    for page in pages:

        if isinstance(page, dict):

            value = page.get("text") or ""

        else:

            value = str(page or "")

        if value.strip():

            page_texts.append(
                value.strip()
            )

    return "\n\n".join(
        page_texts
    ).strip()


# =========================================================
# SECTION EXTRACTION
# =========================================================

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

    start_match = start_pattern.search(
        text
    )

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
        "objectives",
        "aim",
        "purpose",
        "methodology",
        "methods",
        "method",
        "approach",
        "dataset",
        "data set",
        "database",
        "data",
        "evaluation",
        "evaluation metrics",
        "metrics",
        "results",
        "results and discussion",
        "discussion",
        "limitations",
        "limitation",
        "constraints",
        "future work",
        "future directions",
        "future research",
        "further work",
        "research gap",
        "research gaps",
        "gap",
        "open problem",
        "open challenge",
        "findings",
        "key findings",
        "key results",
        "conclusion",
        "conclusions",
        "references",
        "bibliography",
        "prior analysis",
        "prediction of exoplanets",
        "prediction over limited data",
        "background and data",
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

    return remaining[
        :max_chars
    ].strip()


# =========================================================
# RELEVANT CONTEXT
# =========================================================

def _build_relevant_text(
    text: str,
    fields: List[str],
) -> str:

    parts = []

    # Keep enough of the beginning because abstracts,
    # introductions, objectives and dataset descriptions
    # are commonly located there.
    beginning = text[:10000]

    parts.append(
        "BEGINNING OF PAPER\n"
        + beginning
    )

    if "methodology" in fields:

        methodology = _find_section(
            text,
            [
                "methodology",
                "methods",
                "method",
                "approach",
                "experiments",
                "experimental setup",
                "prior analysis",
                "prediction of exoplanets",
                "prediction over limited data",
            ],
            max_chars=7000,
        )

        if methodology:

            parts.append(
                "METHODOLOGY / EXPERIMENTS\n"
                + methodology
            )

    if "dataset" in fields:

        dataset = _find_section(
            text,
            [
                "background and data",
                "dataset",
                "data set",
                "data description",
                "database",
                "data",
            ],
            max_chars=7000,
        )

        if dataset:

            parts.append(
                "DATASET / DATA SECTION\n"
                + dataset
            )

    if "evaluation_metric" in fields:

        results = _find_section(
            text,
            [
                "evaluation",
                "evaluation metrics",
                "metrics",
                "results",
                "results and discussion",
                "prediction of exoplanets",
                "prediction over limited data",
                "conclusion",
            ],
            max_chars=7000,
        )

        if results:

            parts.append(
                "EVALUATION / RESULTS\n"
                + results
            )

    if "limitations" in fields:

        limitations = _find_section(
            text,
            [
                "limitations",
                "limitation",
                "constraints",
            ],
            max_chars=5000,
        )

        if limitations:

            parts.append(
                "EXPLICIT LIMITATIONS\n"
                + limitations
            )

        discussion = _find_section(
            text,
            [
                "discussion",
                "results and discussion",
                "conclusion",
                "conclusions",
            ],
            max_chars=5000,
        )

        if discussion:

            parts.append(
                "DISCUSSION / CONCLUSION\n"
                + discussion
            )

    if "future_work" in fields:

        future_work = _find_section(
            text,
            [
                "future work",
                "future directions",
                "future research",
                "further work",
            ],
            max_chars=5000,
        )

        if future_work:

            parts.append(
                "EXPLICIT FUTURE WORK\n"
                + future_work
            )

    if "research_gap" in fields:

        gap = _find_section(
            text,
            [
                "research gap",
                "research gaps",
                "gap",
                "open problem",
                "open problems",
                "open challenge",
            ],
            max_chars=5000,
        )

        if gap:

            parts.append(
                "RESEARCH GAP\n"
                + gap
            )

    if "findings" in fields:

        findings = _find_section(
            text,
            [
                "findings",
                "key findings",
                "key results",
                "results and findings",
                "conclusion",
                "conclusions",
            ],
            max_chars=6000,
        )

        if findings:

            parts.append(
                "FINDINGS / CONCLUSION\n"
                + findings
            )

    # Prevent excessively large prompts.
    combined = "\n\n".join(parts)

    return combined[:30000]


# =========================================================
# FIELD-SPECIFIC INSTRUCTIONS
# =========================================================

GROUP_INSTRUCTIONS = {

    "main": """
Extract:

1. objective
- State what the authors aim to achieve, investigate,
  detect, classify, predict or evaluate.

2. methodology
- Include the important algorithms/models.
- Include preprocessing techniques.
- Include training/testing procedure.
- Include important experimental settings.
- Include important thresholds or conditions.
- If multiple algorithms are used, mention the important ones,
  not only the best-performing model.

3. dataset
- Preserve the exact dataset name and source.
- Preserve campaign/version names.
- Preserve training/test sample counts.
- Preserve positive/negative class counts.
- Preserve observations per sample.
- Preserve other important dataset characteristics.

4. evaluation_metric
- Include metric names.
- Include important numerical results.
- Include overall performance.
- Include performance under important conditions,
  such as limited/reduced observations.
- Preserve exact percentages.

Do not invent information.
""",

    "results": """
Extract:

1. limitations
- Use limitations explicitly stated by the authors.
- If there is no dedicated limitations section, use concrete
  study constraints directly supported by the discussion/conclusion.
- Do not invent generic limitations.

2. future_work
- ONLY include future work explicitly stated or clearly described
  by the authors.
- Do NOT infer future work from limitations.
- Do NOT propose your own future work.
- If unsupported, return an empty string.

3. research_gap
- Include only a research gap supported by the paper.
- Look for unresolved problems, missing capabilities or
  limitations in previous work described by the authors.
- Do not create a generic research gap.
- If unsupported, return an empty string.

4. findings
- Summarize the main experimentally supported findings.
- Include the most important results.
- Include best-performing methods when clearly stated.
- Include important metric values.
- Include important limited-data findings.
- Include the main conclusion.
""",

    "keywords": """
Extract 5–10 concise technical keywords explicitly supported
by the paper.

Prefer:
- research topic
- algorithms
- datasets
- techniques
- domain terms

Avoid generic words such as:
paper, study, research, results, method.
""",
}


# =========================================================
# GROQ GROUP EXTRACTION
# =========================================================

def _extract_group(
    text: str,
    fields: List[str],
    group_name: str,
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

    context = _build_relevant_text(
        text,
        fields,
    )

    field_list = "\n".join(
        f"- {field}"
        for field in fields
    )

    instructions = GROUP_INSTRUCTIONS.get(
        group_name,
        "",
    )

    if "keywords" in fields:

        keyword_rule = """
For keywords, return a JSON array of 5–10 short technical terms.
"""

    else:

        keyword_rule = ""

    prompt = f"""
{instructions}

FIELDS TO EXTRACT:

{field_list}

SOURCE TEXT:

{context}

OUTPUT RULES:

- Return exactly ONE JSON object.
- Use ONLY the requested field names.
- Do not add extra keys.
- Use only information from the supplied source text.
- Preserve exact technical terminology.
- Preserve exact numerical values.
- Keep each non-empty text field concise and factual.
- Do not invent information.
- Do not use outside knowledge.
- If information is genuinely unsupported, use an empty string.
- For future_work, do not infer or invent future directions.
- For research_gap, do not invent a generic gap.
{keyword_rule}

Expected structure:

{{
    "field1": "...",
    "field2": "...",
    "field3": "..."
}}

Return JSON only.
""".strip()

    # Keep token usage controlled.
    if group_name == "keywords":

        max_tokens = 500

    else:

        max_tokens = 1800

    print(
        "\n"
        + "=" * 60
    )

    print(
        "[Extraction]"
        f" Group={group_name}"
        f" | Fields={fields}"
        f" | Context={len(context)} chars"
        f" | MaxTokens={max_tokens}"
        f" | Model={settings.GROQ_MODEL}"
    )

    print(
        "=" * 60
    )

    try:

        completion = client.chat.completions.create(

            model=settings.GROQ_MODEL,

            temperature=0,

            max_tokens=max_tokens,

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

        error_text = str(exc)

        print(
            "[Extraction ERROR]"
            f" Group={group_name}"
            f" | Error={error_text}"
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Structured extraction failed "
                f"for group '{group_name}': "
                f"{error_text}"
            ),
        ) from exc

    if not completion.choices:

        print(
            "[Extraction]"
            f" No choices returned for {group_name}"
        )

        return _empty_result(fields)

    message = (
        completion
        .choices[0]
        .message
    )

    content = (
        message.content
        or "{}"
    )

    print(
        "[Extraction]"
        f" Group={group_name}"
        f" | ResponseChars={len(content)}"
    )

    result = _parse_json(
        content,
        fields,
    )

    print(
        "[Extraction]"
        f" Completed group={group_name}"
    )

    return result


# =========================================================
# EXTRACT ALL FIELDS
# =========================================================

def _extract_all_fields(
    text: str,
) -> Dict[str, Any]:

    result = _empty_result(
        FIELDS
    )

    # -----------------------------------------------------
    # CALL 1
    # -----------------------------------------------------

    group_one = [
        "objective",
        "methodology",
        "dataset",
        "evaluation_metric",
    ]

    partial_one = _extract_group(
        text,
        group_one,
        "main",
    )

    for field in group_one:

        value = partial_one.get(
            field,
            "",
        )

        if value not in (
            "",
            [],
            {},
        ):

            result[field] = value

    # -----------------------------------------------------
    # CALL 2
    # -----------------------------------------------------

    group_two = [
        "limitations",
        "future_work",
        "research_gap",
        "findings",
    ]

    partial_two = _extract_group(
        text,
        group_two,
        "results",
    )

    for field in group_two:

        value = partial_two.get(
            field,
            "",
        )

        if value not in (
            "",
            [],
            {},
        ):

            result[field] = value

    # -----------------------------------------------------
    # CALL 3
    # -----------------------------------------------------

    group_three = [
        "keywords",
    ]

    partial_three = _extract_group(
        text,
        group_three,
        "keywords",
    )

    keywords = partial_three.get(
        "keywords",
        [],
    )

    if isinstance(
        keywords,
        list,
    ):

        result["keywords"] = [
            str(keyword).strip()
            for keyword in keywords
            if str(keyword).strip()
        ]

    return result


# =========================================================
# MAIN EXTRACTION
# =========================================================

def extract_paper_content(
    paper_id: str,
    paper: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:

    paper_id = str(
        paper_id or ""
    ).strip()

    if not ObjectId.is_valid(
        paper_id
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid paper ID",
        )

    object_id = ObjectId(
        paper_id
    )

    paper = papers_collection.find_one(
        {
            "_id": object_id
        }
    )

    if not paper:

        raise HTTPException(
            status_code=404,
            detail="Paper not found",
        )

    text = _get_paper_text(
        paper
    )

    if not text:

        raise HTTPException(
            status_code=400,
            detail=(
                "Paper has no parsed text. "
                "Run parsing before extraction."
            ),
        )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "[Extraction]"
        f" Paper ID={paper_id}"
    )

    print(
        "[Extraction]"
        f" Paper text={len(text)} chars"
    )

    print(
        "[Extraction]"
        " Starting 3-call extraction"
    )

    print(
        "=" * 70
    )

    fields = _extract_all_fields(
        text
    )

    # =====================================================
    # SAVE EXTRACTION
    # =====================================================

    extraction_document = {
        "paper_id": paper_id,
        **fields,
        "updated_at": datetime.utcnow(),
    }

    extractions_collection.update_one(
        {
            "paper_id": paper_id
        },
        {
            "$set": extraction_document
        },
        upsert=True,
    )

    # =====================================================
    # UPDATE PAPER
    # =====================================================

    papers_collection.update_one(
        {
            "_id": object_id
        },
        {
            "$set": {

                "status": "extracted",

                "extracted_at": (
                    datetime.utcnow()
                ),

                "updated_at": (
                    datetime.utcnow()
                ),

                "objective": fields.get(
                    "objective"
                ),

                "methodology": fields.get(
                    "methodology"
                ),

                "dataset": fields.get(
                    "dataset"
                ),

                "evaluation_metric": fields.get(
                    "evaluation_metric"
                ),

                "limitations": fields.get(
                    "limitations"
                ),

                "future_work": fields.get(
                    "future_work"
                ),

                "research_gap": fields.get(
                    "research_gap"
                ),

                "findings": fields.get(
                    "findings"
                ),

                "keywords": fields.get(
                    "keywords",
                    [],
                ),
            }
        },
    )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "[Extraction]"
        " EXTRACTION SUCCESSFULLY SAVED"
    )

    print(
        "=" * 70
    )

    return fields


# =========================================================
# BACKWARD COMPATIBILITY
# =========================================================

extract_fields_for_paper = (
    extract_paper_content
)