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
from models.certificate_model import get_certificate_by_cid, get_certificate_by_id
from services.ai_service import compare_certificates
from services.blockchain_service import validate_chain, find_block_by_cid


verify_bp = Blueprint("verify", __name__)


@verify_bp.route("/verify/<int:cert_id>", methods=["GET", "POST"])
async def verify_certificate(cert_id: int):

    cert = await asyncio.to_thread(get_certificate_by_id, cert_id)

    if not cert:
        flash("Certificate not found.", "danger")

    cid = cert.cid if cert else None
    # Validate chain in thread to avoid blocking event loop
    chain_valid = await asyncio.to_thread(validate_chain)
    block = await asyncio.to_thread(find_block_by_cid, cid) if cid else None
    blockchain_verified = bool(block and chain_valid)
    trust_score = None
    heatmap_path = None

    # Read precomputed AI metadata (if present) to avoid heavy processing on GET.
    blockchain_tx = None
    if cert:
        meta_path = FINAL_UPLOAD_DIR / f"meta_{cert.id}.json"
        if meta_path.exists():
            try:
                import json

                def _read_meta(p):
                    with open(p, "r", encoding="utf-8") as mf:
                        return json.load(mf)

                meta = await asyncio.to_thread(_read_meta, meta_path)
                trust_score = meta.get("trust_score")
                heatmap_path = meta.get("heatmap")
                blockchain_tx = meta.get("blockchain_tx")
            except Exception:
                trust_score = None
                heatmap_path = None
                blockchain_tx = None
        else:
            blockchain_tx = getattr(cert, "blockchain_tx", None)

    # If a visitor uploads a file for manual recheck, run comparison against stored original
    if request.method == "POST" and "certificate_file" in request.files:
        file = request.files["certificate_file"]
        if file and file.filename:
            TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            filename = f"verify_{cert_id}_{file.filename.replace(' ', '_')}"
            upload_path = TEMP_UPLOAD_DIR / filename
            file.save(upload_path)

            if not cert:
                flash("Original certificate not found in database.", "danger")
            else:
                original_image_path = FINAL_UPLOAD_DIR / cert.image_filename
                try:
                    # Run expensive AI comparison in thread to avoid blocking
                    trust_score, heatmap_rel = await asyncio.to_thread(
                        compare_certificates, str(original_image_path), str(upload_path)
                    )
                    heatmap_path = heatmap_rel
                except Exception as exc:  # pragma: no cover - defensive
                    flash(f"AI recheck failed: {exc}", "danger")

    return render_template(
        "verify.html",
        cert_id=cert_id,
        cid=cid,
        blockchain_verified=blockchain_verified,
        chain_valid=chain_valid,
        certificate=cert,
        trust_score=trust_score,
        heatmap_path=heatmap_path,
        blockchain_tx=blockchain_tx,
    )

