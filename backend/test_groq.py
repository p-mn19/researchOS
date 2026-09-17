from groq import Groq

from app.config import settings


api_key = settings.GROQ_API_KEY.strip()

if not api_key:
    raise RuntimeError(
        "GROQ_API_KEY was not loaded from backend/.env"
    )

client = Groq(
    api_key=api_key,
    base_url="https://api.groq.com",
    timeout=30.0,
    max_retries=2,
)

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