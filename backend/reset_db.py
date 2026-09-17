import shutil

from app.config import STORAGE_DIR
from app.db import (
    chunks_collection,
    extractions_collection,
    papers_collection,
)


def main():
    papers_deleted = papers_collection.delete_many(
        {}
    ).deleted_count

    chunks_deleted = chunks_collection.delete_many(
        {}
    ).deleted_count

    extractions_deleted = (
        extractions_collection.delete_many(
            {}
        ).deleted_count
    )

    removed_files = 0

    if STORAGE_DIR.exists():
        for path in STORAGE_DIR.iterdir():
            if path.is_file():
                path.unlink()
                removed_files += 1

            elif path.is_dir():
                shutil.rmtree(path)
                removed_files += 1

    print(
        "Database reset completed."
    )
    print(
        f"Papers deleted: {papers_deleted}"
    )
    print(
        f"Chunks deleted: {chunks_deleted}"
    )
    print(
        f"Extractions deleted: {extractions_deleted}"
    )
    print(
        f"Stored files removed: {removed_files}"
    )


if __name__ == "__main__":
    main()