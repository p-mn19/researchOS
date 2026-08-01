from pymongo import MongoClient
from app.config import settings

client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
db = client[settings.MONGODB_DB]

papers_collection = db["papers"]
chunks_collection = db["paper_chunks"]
extractions_collection = db["paper_extractions"]