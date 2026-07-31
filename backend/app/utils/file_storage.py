import os
import uuid
from fastapi import UploadFile
from app.core.config import settings


def ensure_storage_dir():
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)


def save_pdf_locally(file: UploadFile):
    ensure_storage_dir()

    ext = os.path.splitext(file.filename)[1].lower()
    if ext != ".pdf":
        ext = ".pdf"

    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(settings.STORAGE_DIR, unique_name)

    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return unique_name, file_path, len(content)