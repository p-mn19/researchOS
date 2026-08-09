from bson import ObjectId
from app.db import extractions_collection, papers_collection


def compare_papers(paper_ids):
    rows = []
    extracted_docs = list(extractions_collection.find({"paper_id": {"$in": paper_ids}}))
    paper_map = {}

    object_ids = [ObjectId(pid) for pid in paper_ids if ObjectId.is_valid(pid)]
    for p in papers_collection.find({"_id": {"$in": object_ids}}):
        paper_map[str(p["_id"])] = p.get("title") or p.get("filename") or "Untitled paper"

    fields = ["methodology", "dataset", "evaluation_metric", "limitations", "future_work"]

    for field in fields:
        row = {"field": field, "values": {}}

        for pid in paper_ids:
            paper_title = paper_map.get(pid, pid)
            row["values"][paper_title] = "—"

        for doc in extracted_docs:
            pid = doc.get("paper_id")
            paper_title = paper_map.get(pid, pid)
            value = doc.get(field, "")
            row["values"][paper_title] = value if value else "—"

        rows.append(row)

    return {"rows": rows, "paper_map": paper_map}