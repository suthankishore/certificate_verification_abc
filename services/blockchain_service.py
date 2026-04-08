import json
import time
from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import BLOCKCHAIN_PATH
from models.certificate_model import (
    insert_certificate,
    update_certificate_files,
    update_certificate_verification,
)
from services.hash_service import hash_file_sha256
from services.ipfs_service import upload_to_ipfs_local
from services.pdf_service import create_temp_certificate_pdf, embed_qr_and_create_final_pdf
from services.qr_service import generate_qr_for_certificate_id
from services.ai_service import compare_certificates
import json


@dataclass
class Block:
    index: int
    timestamp: float
    certificate_hash: str
    cid: str
    previous_hash: str
    current_hash: str


def _ensure_chain_file() -> None:
    BLOCKCHAIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BLOCKCHAIN_PATH.exists():
        genesis_block = Block(
            index=0,
            timestamp=time.time(),
            certificate_hash="GENESIS",
            cid="GENESIS",
            previous_hash="0",
            current_hash="",
        )
        genesis_block.current_hash = _hash_block(genesis_block)
        with BLOCKCHAIN_PATH.open("w", encoding="utf-8") as f:
            json.dump([asdict(genesis_block)], f, indent=2)


def initialize_blockchain() -> None:
    """
    Ensure blockchain file and genesis block exist.
    """
    _ensure_chain_file()


def _load_chain() -> List[Block]:
    _ensure_chain_file()
    with BLOCKCHAIN_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return [Block(**b) for b in data]


def _save_chain(chain: List[Block]) -> None:
    with BLOCKCHAIN_PATH.open("w", encoding="utf-8") as f:
        json.dump([asdict(b) for b in chain], f, indent=2)


def _hash_block(block: Block) -> str:
    block_dict = asdict(block).copy()
    block_dict["current_hash"] = ""
    encoded = json.dumps(block_dict, sort_keys=True).encode()
    return sha256(encoded).hexdigest()


def add_block(certificate_hash: str, cid: str) -> Block:
    """
    STEP 4: Append a new block with certificate hash and CID.
    """
    chain = _load_chain()
    last_block = chain[-1]
    index = last_block.index + 1
    timestamp = time.time()
    previous_hash = last_block.current_hash
    new_block = Block(
        index=index,
        timestamp=timestamp,
        certificate_hash=certificate_hash,
        cid=cid,
        previous_hash=previous_hash,
        current_hash="",
    )
    new_block.current_hash = _hash_block(new_block)
    chain.append(new_block)
    _save_chain(chain)
    return new_block


def validate_chain() -> bool:
    """
    Ensure blockchain integrity.
    """
    chain = _load_chain()
    for i in range(1, len(chain)):
        prev = chain[i - 1]
        curr = chain[i]
        if curr.previous_hash != prev.current_hash:
            return False
        if _hash_block(curr) != curr.current_hash:
            return False
    return True


def find_block_by_cid(cid: str) -> Optional[Block]:
    chain = _load_chain()
    for block in chain:
        if block.cid == cid:
            return block
    return None


def issue_certificate_workflow(
    student_name: str,
    register_number: str,
    course: str,
    issue_date: str,
) -> Dict[str, Any]:
    """
    Fully automated certificate issuance workflow implementing the required steps.

    Returns a dict with keys:
        certificate_id, cid, blockchain_index, final_pdf_path,
        final_image_path
    """
    # STEP 1: temporary certificate PDF
    temp_pdf_path, base_image_path = create_temp_certificate_pdf(
        student_name=student_name,
        register_number=register_number,
        course=course,
        issue_date=issue_date,
    )

    # STEP 2: SHA256 hash of PDF
    cert_hash = hash_file_sha256(str(temp_pdf_path))

    # STEP 3: Upload certificate to IPFS-like storage
    cid = upload_to_ipfs_local(str(temp_pdf_path))

    # STEP 4: store in blockchain
    block = add_block(cert_hash, cid)

    # STEP 5: insert a DB record now with placeholder filenames so we have a certificate_id
    # Read the image data
    with final_image_path.open("rb") as f:
        image_data = f.read()
    
    cert_id = insert_certificate(
        student_name=student_name,
        register_number=register_number,
        course=course,
        issue_date=issue_date,
        cid=cid,
        blockchain_index=block.index,
        pdf_filename="",
        image_filename=Path(final_image_path).name,
        image_data=image_data,
    )

    # STEP 6: generate QR that points to verification by certificate ID
    qr_path = generate_qr_for_certificate_id(cert_id)

    # STEP 7: embed QR and save final PDF
    final_pdf_path, final_image_path = embed_qr_and_create_final_pdf(
        base_image_path=base_image_path,
        qr_image_path=qr_path,
    )

    # STEP 8: update DB record with final filenames
    update_certificate_files(cert_id, Path(final_pdf_path).name, Path(final_image_path).name)

    # STEP 9: run AI forgery detection once in backend (silently) to precompute baseline
    try:
        trust_score, heatmap_rel = compare_certificates(str(final_image_path), str(final_image_path))
    except Exception:
        trust_score, heatmap_rel = None, None

    # Save metadata for fast verification page loads
    meta = {
        "trust_score": trust_score,
        "heatmap": heatmap_rel,
        "cid": cid,
        "blockchain_index": block.index,
        "blockchain_tx": block.current_hash,
    }
    meta_path = Path(final_image_path).parent / f"meta_{cert_id}.json"
    try:
        with meta_path.open("w", encoding="utf-8") as mf:
            json.dump(meta, mf)
    except Exception:
        pass

    # Persist AI and blockchain tx into the certificate record for fast reads
    try:
        update_certificate_verification(cert_id, trust_score, heatmap_rel, block.current_hash)
    except Exception:
        pass

    # STEP 9: caller can render preview page
    return {
        "certificate_id": cert_id,
        "cid": cid,
        "blockchain_index": block.index,
        "final_pdf_path": str(final_pdf_path),
        "final_image_path": str(final_image_path),
    }

