from flask import Blueprint, flash, render_template, request
from werkzeug.utils import secure_filename

from config import FINAL_UPLOAD_DIR, TEMP_UPLOAD_DIR
from models.certificate_model import get_certificate_by_id
from services.ai_service import compare_certificates
from services.blockchain_service import find_block_by_cid, validate_chain

verify_bp = Blueprint("verify", __name__)


@verify_bp.route("/verify/<int:cert_id>", methods=["GET", "POST"])
def verify_certificate(cert_id: int):

    print("👉 PAGE OPEN:", cert_id)

    cert = get_certificate_by_id(cert_id)
    trust_score = None
    heatmap_path = None
    blockchain_tx = None

    if not cert:
        flash("Certificate not found.", "danger")
        cid = None
        blockchain_verified = False
        chain_valid = False
    else:
        cid = cert.cid
        chain_valid = validate_chain()
        block = find_block_by_cid(cid) if cid else None
        blockchain_verified = bool(block and chain_valid)
        blockchain_tx = getattr(cert, "blockchain_tx", None)

    # 🔥 POST HANDLING (FIXED)
    if request.method == "POST":
        print("🔥 POST HIT")

        uploaded_file = request.files.get("certificate_file")

        if uploaded_file is None:
            print("❌ No file key in request")
            flash("No file part in request.", "danger")

        elif uploaded_file.filename == "":
            print("❌ Empty filename")
            flash("Please choose a certificate file.", "danger")

        else:
            print("✅ File received:", uploaded_file.filename)

            if not cert:
                flash("Original certificate not found.", "danger")
            else:
                TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

                filename = secure_filename(uploaded_file.filename)
                upload_path = TEMP_UPLOAD_DIR / f"verify_{cert_id}_{filename}"

                uploaded_file.save(upload_path)
                print("📁 Saved to:", upload_path)

                original_image_path = FINAL_UPLOAD_DIR / cert.image_filename

                try:
                    trust_score, heatmap_rel = compare_certificates(
                        str(original_image_path),
                        str(upload_path),
                    )

                    heatmap_path = heatmap_rel
                    print("🔥 AI RESULT:", trust_score)

                except Exception as exc:
                    print("❌ AI ERROR:", exc)
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