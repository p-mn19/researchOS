import chromadb
from app.config import VECTOR_DIR
from app.db import chunks_collection
from app.services.embedding_service import embed_texts

client = chromadb.PersistentClient(path=str(VECTOR_DIR))
collection = client.get_or_create_collection("research_papers")

def index_paper_chunks(paper_id: str):
    chunks = list(chunks_collection.find({"paper_id": paper_id}))
    if not chunks:
        raise ValueError("No chunks found for paper")

    ids = [str(c["_id"]) for c in chunks]
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)
    metadatas = [{
        "paper_id": c["paper_id"],
        "chunk_index": c["chunk_index"],
        "section_title": c.get("section_title", "Unknown"),
    } for c in chunks]

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return {"paper_id": paper_id, "indexed_count": len(ids)}