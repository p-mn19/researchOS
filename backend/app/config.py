from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Create the vector directory using Path
_vector_dir_path = BASE_DIR / "vector_store"
_vector_dir_path.mkdir(parents=True, exist_ok=True)

# Export VECTOR_DIR globally as a standard string for other files to import
VECTOR_DIR = str(_vector_dir_path)

class Settings(BaseSettings):
    APP_NAME: str = "ResearchOS Backend"
    FRONTEND_URL: str = "http://localhost:3000"  # <-- Added this for CORS!
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "researchos_db"
    storage_dir: str = "storage/papers"
    vector_dir: str = str(_vector_dir_path)

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

settings = Settings()