import fitz
from datetime import datetime
from bson import ObjectId
from app.db import papers_collection

def parse_pdf_text(paper_id: str):
    paper = papers_collection.find_one({"_id": ObjectId(paper_id)})
    if not paper:
        raise ValueError("Paper not found")

    doc = fitz.open(paper["filepath"])
    pages = []
    full_text = []

    for i, page in enumerate(doc):
        text = page.get_text("text")
        pages.append({
            "page_number": i + 1,
            "text": text
        })
        full_text.append(text)

    combined_text = "\n".join(full_text)

    papers_collection.update_one(
        {"_id": ObjectId(paper_id)},
        {
            "$set": {
                "raw_text": combined_text,
                "pages": pages,
                "status": "parsed",
                "parsed_at": datetime.utcnow(),
            }
        }
    )

    return {
        "paper_id": paper_id,
        "pages_count": len(pages),
        "status": "parsed"
    }