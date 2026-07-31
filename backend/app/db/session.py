from pymongo import MongoClient
from app.core.config import settings

client = MongoClient(settings.MONGODB_URL)
database = client[settings.DATABASE_NAME]

papers_collection = database["papers"]