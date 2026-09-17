from pymongo import MongoClient


from app.config import settings


client = MongoClient(
    settings.MONGODB_URL,
    serverSelectionTimeoutMS=5000,
)


database = client[settings.MONGODB_DB]


papers_collection = database["papers"]
chunks_collection = database["chunks"]
extractions_collection = database["extractions"]
reviews_collection = database["reviews"]
