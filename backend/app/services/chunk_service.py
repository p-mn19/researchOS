from bson import ObjectId
from app.db import papers_collection, chunks_collection

def split_text(text: str, chunk_size: int = 1200, overlap: int = 200):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def chunk_paper(paper_id: str):
    paper = papers_collection.find_one({"_id": ObjectId(paper_id)})
    if not paper or "raw_text" not in paper:
        raise ValueError("Paper not parsed")

    chunks_collection.delete_many({"paper_id": paper_id})
    chunks = split_text(paper["raw_text"])

    docs = []
    for i, chunk in enumerate(chunks):
        docs.append({
            "paper_id": paper_id,
            "chunk_index": i,
            "section_title": "Unknown",
            "page_number": None,
            "text": chunk,
        })

    if docs:
        chunks_collection.insert_many(docs)

    return {"paper_id": paper_id, "chunks_created": len(docs)}