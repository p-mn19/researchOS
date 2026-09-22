from app.config import settings
from app.services.groq_client import get_groq_client


if not settings.groq_api_keys:
    raise RuntimeError(
        "GROQ_API_KEY or GROQ_API_KEYS was not loaded from backend/.env"
    )

client = get_groq_client(timeout=30.0, max_retries=2)
assert client is not None

try:
    models = client.models.list()

    print("Groq connection successful.")
    print("Configured model:", settings.GROQ_MODEL)

    data = getattr(models, "data", [])
    print("Models returned:", len(data))

    for model in data[:10]:
        print("-", model.id)

except Exception as exc:
    print("Groq connection failed.")
    print("Error type:", type(exc).__name__)
    print("Error details:", repr(exc))
    raise
