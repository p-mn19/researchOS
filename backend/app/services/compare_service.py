from bson import ObjectId
from app.db import extractions_collection, papers_collection

def compare_papers(paper_ids):
    rows = []
    extracted_docs = list(extractions_collection.find({"paper_id": {"$in": paper_ids}}))
    paper_map = {}
    for p in papers_collection.find({"_id": {"$in": [ObjectId(pid) for pid in paper_ids]}}):
        paper_map[str(p["_id"])] = p.get("title") or p.get("filename")

    fields = ["methodology", "dataset", "evaluation_metric", "limitations", "future_work"]

    for field in fields:
        row = {"field": field, "values": {}}
        for doc in extracted_docs:
            row["values"][paper_map.get(doc["paper_id"], doc["paper_id"])] = doc.get(field, "")
        rows.append(row)

    return {"rows": rows}