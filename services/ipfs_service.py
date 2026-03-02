import shutil
import uuid
from pathlib import Path

from config import IPFS_STORAGE_DIR


def _ensure_storage() -> None:
    IPFS_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def upload_to_ipfs_local(file_path: str) -> str:
    """
    Local, filesystem-based implementation that mimics IPFS-style CIDs.
    This is a real implementation that stores files under IPFS_STORAGE_DIR.
    """
    _ensure_storage()
    src = Path(file_path)
    # CID-like identifier
    cid = uuid.uuid4().hex
    dest = IPFS_STORAGE_DIR / f"{cid}{src.suffix}"
    shutil.copy2(src, dest)
    return cid


def get_ipfs_file_path(cid: str) -> Path:
    """
    Return the stored file path for a given CID, if it exists.
    """
    _ensure_storage()
    for p in IPFS_STORAGE_DIR.glob(f"{cid}.*"):
        return p
    return IPFS_STORAGE_DIR / f"{cid}"

