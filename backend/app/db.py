from pymongo import MongoClient

from app.config import settings


client = MongoClient(
    settings.mongodb_url,
    serverSelectionTimeoutMS=5000,
)

db = client[settings.database_name]

papers_collection = db["papers"]
extractions_collection = db["extractions"]
chunks_collection = db["chunks"]