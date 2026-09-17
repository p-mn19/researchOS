from datetime import datetime
from typing import Any, Dict, List, Optional


from bson import ObjectId
from fastapi import HTTPException


from app.db import projects_collection, research_gaps_collection, drafts_collection
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ResearchGapSummaryCreate,
    ResearchGapSummary,
    ResearchIdea,
    ResearchIdeaCreate,
    ManuscriptDraft,
    ManuscriptDraftCreate,
)


def _serialize_project(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "title": doc.get("title", ""),
        "description": doc.get("description"),
        "user_id": doc.get("user_id"),
        "paper_ids": doc.get("paper_ids", []),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


def create_project(data: ProjectCreate) -> ProjectResponse:
    now = datetime.utcnow()

    document = {
        "title": data.title,
        "description": data.description,
        "user_id": data.user_id,
        "paper_ids": [],
        "created_at": now,
        "updated_at": now,
    }

    result = projects_collection.insert_one(document)

    return ProjectResponse(
        id=str(result.inserted_id),
        title=document["title"],
        description=document["description"],
        user_id=document["user_id"],
        paper_ids=document["paper_ids"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def list_projects(user_id: Optional[str] = None) -> List[ProjectResponse]:
    query = {}
    if user_id:
        query["user_id"] = user_id

    docs = projects_collection.find(query).sort("updated_at", -1)

    return [
        ProjectResponse(**_serialize_project(doc))
        for doc in docs
    ]


def get_project_by_id(project_id: str) -> ProjectResponse:
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")

    doc = projects_collection.find_one({"_id": ObjectId(project_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse(**_serialize_project(doc))


def update_project(project_id: str, data: ProjectUpdate) -> ProjectResponse:
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")

    updates = {}
    if data.title is not None:
        updates["title"] = data.title
    if data.description is not None:
        updates["description"] = data.description

    if not updates:
        return get_project_by_id(project_id)

    updates["updated_at"] = datetime.utcnow()

    result = projects_collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": updates},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")

    return get_project_by_id(project_id)


def add_papers_to_project(project_id: str, paper_ids: List[str]) -> ProjectResponse:
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")

    project = projects_collection.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = set(project.get("paper_ids", []))
    new_ids = [str(pid) for pid in paper_ids if str(pid) not in existing]

    if not new_ids:
        return get_project_by_id(project_id)

    projects_collection.update_one(
        {"_id": ObjectId(project_id)},
        {
            "$addToSet": {"paper_ids": {"$each": new_ids}},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )

    return get_project_by_id(project_id)


# -------------------------
# Module 8 — Research gap
# -------------------------


def _serialize_research_gap(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "project_id": doc.get("project_id"),
        "gap_description": doc.get("gap_description", ""),
        "key_themes": doc.get("key_themes", []),
        "recurring_limitations": doc.get("recurring_limitations", []),
        "candidate_methodologies": doc.get("candidate_methodologies", []),
        "suggested_ideas": doc.get("suggested_ideas", []),
        "updated_at": doc.get("updated_at"),
    }


def create_or_update_research_gap(
    project_id: Optional[str],
    data: ResearchGapSummaryCreate,
) -> ResearchGapSummary:
    # For simplicity, one gap per project; adjust if you need versions.
    query = {"project_id": project_id} if project_id else {"project_id": None}

    now = datetime.utcnow()

    # Convert idea inputs to full idea objects with IDs
    suggested_ideas: List[Dict[str, Any]] = []
    for i, idea_in in enumerate(data.suggested_idea_inputs):
        idea_id = f"{project_id or 'global'}_idea_{i}"
        idea_obj = {
            "id": idea_id,
            "project_id": project_id,
            "title": idea_in.title,
            "problem_statement": idea_in.problem_statement,
            "hypothesis": idea_in.hypothesis,
            "suggested_methodology": idea_in.suggested_methodology,
            "related_paper_ids": idea_in.related_paper_ids,
            "confidence": idea_in.confidence,
            "created_at": now,
        }
        suggested_ideas.append(idea_obj)

    document = {
        "project_id": project_id,
        "gap_description": data.gap_description,
        "key_themes": data.key_themes,
        "recurring_limitations": data.recurring_limitations,
        "candidate_methodologies": data.candidate_methodologies,
        "suggested_ideas": suggested_ideas,
        "updated_at": now,
    }

    research_gaps_collection.update_one(
        query,
        {"$set": document},
        upsert=True,
    )

    stored = research_gaps_collection.find_one(query)
    if not stored:
        raise HTTPException(status_code=500, detail="Failed to store research gap")

    return ResearchGapSummary(**_serialize_research_gap(stored))


def get_research_gap_by_project(project_id: Optional[str]) -> Optional[ResearchGapSummary]:
    query = {"project_id": project_id} if project_id else {"project_id": None}
    doc = research_gaps_collection.find_one(query)
    if not doc:
        return None
    return ResearchGapSummary(**_serialize_research_gap(doc))


# -------------------------
# Module 9 — Drafting
# -------------------------


def _serialize_draft(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "project_id": doc.get("project_id"),
        "title": doc.get("title"),
        "section_plans": doc.get("section_plans", []),
        "content": doc.get("content", {}),
        "citations": doc.get("citations", []),
        "status": doc.get("status", "draft"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


def create_manuscript_draft(data: ManuscriptDraftCreate) -> ManuscriptDraft:
    now = datetime.utcnow()

    document = {
        "project_id": data.project_id,
        "title": data.title,
        "section_plans": data.section_plans,
        "content": data.content or {},
        "citations": data.citations or [],
        "status": "draft",
        "created_at": now,
        "updated_at": now,
    }

    result = drafts_collection.insert_one(document)

    return ManuscriptDraft(
        id=str(result.inserted_id),
        project_id=document["project_id"],
        title=document["title"],
        section_plans=document["section_plans"],
        content=document["content"],
        citations=document["citations"],
        status=document["status"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def get_draft_by_id(draft_id: str) -> ManuscriptDraft:
    if not ObjectId.is_valid(draft_id):
        raise HTTPException(status_code=400, detail="Invalid draft ID")

    doc = drafts_collection.find_one({"_id": ObjectId(draft_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Draft not found")

    return ManuscriptDraft(**_serialize_draft(doc))


def update_draft_content(
    draft_id: str,
    section_name: str,
    content: str,
    citations: Optional[List[Dict[str, Any]]] = None,
) -> ManuscriptDraft:
    if not ObjectId.is_valid(draft_id):
        raise HTTPException(status_code=400, detail="Invalid draft ID")

    draft = drafts_collection.find_one({"_id": ObjectId(draft_id)})
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    current_content = draft.get("content", {}) or {}
    current_content[section_name] = content

    updates = {
        "content": current_content,
        "updated_at": datetime.utcnow(),
    }

    if citations is not None:
        updates["citations"] = citations

    drafts_collection.update_one(
        {"_id": ObjectId(draft_id)},
        {"$set": updates},
    )

    return get_draft_by_id(draft_id)