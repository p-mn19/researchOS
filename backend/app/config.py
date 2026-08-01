from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage" / "papers"
VECTOR_DIR = BASE_DIR / "storage" / "vectors"

class Settings(BaseSettings):
    APP_NAME: str = "ResearchOS Backend"
    APP_ENV: str = "dev"
    FRONTEND_URL: str = "http://localhost:3000"

    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "researchos"

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    TOP_K: int = 5

    class Config:
        env_file = ".env"

settings = Settings()
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DIR.mkdir(parents=True, exist_ok=True)