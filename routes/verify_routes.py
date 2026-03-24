import os
from pathlib import Path

from flask import (
    Blueprint,
    render_template,
    request,
    flash,
)
import asyncio

from config import TEMP_UPLOAD_DIR, FINAL_UPLOAD_DIR
from models.certificate_model import get_certificate_by_cid, get_certificate_by_id, update_certificate_verification
from services.ai_service import compare_certificates
from services.blockchain_service import validate_chain, find_block_by_cid
from services.qr_service import extract_cid_from_qr_image
from services.hash_service import hash_file_sha256


verify_bp = Blueprint("verify", __name__)


@verify_bp.route("/verify", methods=["GET", "POST"])
@verify_bp.route("/verify/<int:cert_id>", methods=["GET", "POST"])
async def verify_certificate(cert_id: int | None = None):
    # Primary identification from URL param or query param
    query_cid = request.args.get("cid")
    cert = None
    fetched_cid = None

    if cert_id is not None:
        cert = await asyncio.to_thread(get_certificate_by_id, cert_id)
    elif query_cid:
        cert = await asyncio.to_thread(get_certificate_by_cid, query_cid)

    if cert:
        fetched_cid = cert.cid

    chain_valid = await asyncio.to_thread(validate_chain)
    block = None
    blockchain_verified = False
    trust_score = None
    heatmap_path = None
    blockchain_tx = None

    if cert and fetched_cid:
        block = await asyncio.to_thread(find_block_by_cid, fetched_cid)
        if block:
            # Validate blockchain integrity only (no file dependency for basic verification)
            blockchain_verified = chain_valid
            blockchain_tx = block.current_hash
        else:
            blockchain_verified = False

    if cert and not blockchain_tx:
        blockchain_tx = getattr(cert, "blockchain_tx", None)

    if not cert and query_cid:
        # still show history for CID-based check even if no DB record exists
        fetched_cid = query_cid

    if request.method == "POST" and "certificate_file" in request.files:
        file = request.files["certificate_file"]
        if file and file.filename:
            TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            filename = f"verify_{cert_id or 'unknown'}_{file.filename.replace(' ', '_')}"
            upload_path = TEMP_UPLOAD_DIR / filename
            file.save(upload_path)

            parsed_cid = extract_cid_from_qr_image(str(upload_path))
            if parsed_cid:
                if parsed_cid.isdigit():
                    cert_id = int(parsed_cid)
                    cert = await asyncio.to_thread(get_certificate_by_id, cert_id)
                else:
                    cert = await asyncio.to_thread(get_certificate_by_cid, parsed_cid)
                if cert:
                    cert_id = cert.id
                    fetched_cid = cert.cid
                block = await asyncio.to_thread(find_block_by_cid, fetched_cid) if fetched_cid else None
                blockchain_verified = bool(chain_valid and block)
                blockchain_tx = block.current_hash if block else None
            else:
                flash(
                    "No QR code with CID found in uploaded file. Ensure the certificate image contains the embedded QR code.",
                    "danger",
                )

            # AI tampering detection in all cases after blockchain check
            if cert and cert.image_filename:
                original_image_path = FINAL_UPLOAD_DIR / cert.image_filename
                if original_image_path.exists():
                    try:
                        trust_score, heatmap_rel = await asyncio.to_thread(
                            compare_certificates, str(original_image_path), str(upload_path)
                        )
                        # Calculate trust score: Blockchain +60, Content +20, Logo/Signature +20
                        blockchain_score = 60 if blockchain_verified else 0
                        content_score = 20 if trust_score > 80 else (trust_score / 100 * 20)
                        logo_sig_score = 20 if trust_score > 90 else 0
                        trust_score = blockchain_score + content_score + logo_sig_score
                        heatmap_path = heatmap_rel
                        update_certificate_verification(cert.id, trust_score, heatmap_path, blockchain_tx)
                    except Exception as exc:  # pragma: no cover - defensive
                        flash(f"AI recheck failed: {exc}", "danger")
                else:
                    flash("Original certificate image not found for AI comparison.", "warning")

    # Avoid presenting None as CID in the template when no data available
    cid_display = fetched_cid if fetched_cid else "(not found)"

    return render_template(
        "verify.html",
        cert_id=cert_id,
        cid=cid_display,
        blockchain_verified=blockchain_verified,
        chain_valid=chain_valid,
        certificate=cert,
        trust_score=trust_score,
        heatmap_path=heatmap_path,
        blockchain_tx=blockchain_tx,
    )

