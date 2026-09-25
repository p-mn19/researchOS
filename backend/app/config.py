from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_STORAGE_DIR = BASE_DIR / "uploads"
DEFAULT_VECTOR_DIR = BASE_DIR / "vector_store"


DEFAULT_STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DEFAULT_VECTOR_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


class Settings(BaseSettings):
    APP_NAME: str = "ResearchOS Backend"
    APP_ENV: str = "development"

    FRONTEND_URL: str = (
        "http://localhost:3000"
    )

    MONGODB_URL: str = (
        "mongodb://127.0.0.1:27017"
    )

    MONGODB_DB: str = "researchos"

    STORAGE_DIR: str = str(DEFAULT_STORAGE_DIR)
    VECTOR_DIR: str = str(DEFAULT_VECTOR_DIR)

    GROQ_API_KEY: str = ""

    GROQ_API_KEYS: str = ""

    GROQ_MODEL: str = (
        "openai/gpt-oss-20b"
    )

    @property
    def groq_api_keys(self) -> tuple[str, ...]:
        """Return configured Groq keys in their configured rotation order."""

        raw_keys = (
            self.GROQ_API_KEYS
            .replace("\n", ",")
            .replace(";", ",")
        )

        keys = [
            key.strip()
            for key in raw_keys.split(",")
            if key.strip()
        ]

        # GROQ_API_KEYS takes precedence.
        # GROQ_API_KEY is the fallback.
        if not keys and self.GROQ_API_KEY.strip():
            keys = [
                self.GROQ_API_KEY.strip()
            ]

        # Remove duplicate keys while
        # preserving their order.
        return tuple(
            dict.fromkeys(keys)
        )

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


STORAGE_DIR = Path(
    settings.STORAGE_DIR
)

VECTOR_DIR = Path(
    settings.VECTOR_DIR
)


STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

VECTOR_DIR.mkdir(
    parents=True,
    exist_ok=True,
)