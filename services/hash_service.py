import hashlib
from pathlib import Path


def hash_file_sha256(file_path: str) -> str:
    """
    Compute SHA256 hash of a file in a memory-efficient way.
    """
    h = hashlib.sha256()
    path = Path(file_path)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

