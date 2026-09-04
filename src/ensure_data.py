"""Restore the search corpus onto Render's persistent disk on first boot."""

import os
import sys
import tarfile
from pathlib import Path
from urllib.request import Request, urlopen


DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
ARCHIVE_URL = os.getenv("DATA_ARCHIVE_URL")
REQUIRED_PATHS = (
    DATA_DIR / "chroma",
    DATA_DIR / "transcripts",
    DATA_DIR / "bm25_index.pkl",
)


def corpus_is_ready() -> bool:
    return all(path.exists() for path in REQUIRED_PATHS)


def main() -> None:
    if corpus_is_ready():
        print(f"Search data is ready at {DATA_DIR}")
        return

    if not ARCHIVE_URL:
        missing = ", ".join(str(path) for path in REQUIRED_PATHS if not path.exists())
        sys.exit(
            "Search data is missing and DATA_ARCHIVE_URL is not configured. "
            f"Missing: {missing}"
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Restoring search data into {DATA_DIR}...")

    request = Request(ARCHIVE_URL, headers={"User-Agent": "yard-search-render-bootstrap/1.0"})
    with urlopen(request, timeout=60) as response:
        # Streaming extraction avoids storing both a multi-gigabyte archive and
        # its extracted contents on the persistent disk.
        with tarfile.open(fileobj=response, mode="r|gz") as archive:
            archive.extractall(DATA_DIR, filter="data")

    if not corpus_is_ready():
        missing = ", ".join(str(path) for path in REQUIRED_PATHS if not path.exists())
        sys.exit(f"The data archive was extracted but is incomplete. Missing: {missing}")

    print("Search data restore complete.")


if __name__ == "__main__":
    main()
