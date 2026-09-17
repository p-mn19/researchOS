from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.answer_service import generate_grounded_answer
from app.services.search_service import semantic_search


router = APIRouter(
    prefix="/papers",
    tags=["answers"],
)


class AnswerRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=10)


@router.post("/{paper_id}/answer")
def answer_paper_question(
    paper_id: str,
    payload: AnswerRequest,
) -> Dict[str, Any]:
    question = payload.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty",
        )

    chunks: List[Dict[str, Any]] = semantic_search(
        query=question,
        paper_ids=[paper_id],
        top_k=payload.top_k,
    )

    result = generate_grounded_answer(
        question=question,
        chunks=chunks,
    )

    return {
        "paper_id": paper_id,
        "question": question,
        **result,
    }