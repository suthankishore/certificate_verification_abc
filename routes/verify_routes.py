from flask import Blueprint, flash, render_template, request
from werkzeug.utils import secure_filename

from config import FINAL_UPLOAD_DIR, TEMP_UPLOAD_DIR
from models.certificate_model import get_certificate_by_id, get_certificate_by_cid
from services.ai_service import (
    compare_certificates,
    convert_pdf_to_image,
)
from services.blockchain_service import find_block_by_cid, validate_chain
from services.hash_service import hash_file_sha256

verify_bp = Blueprint("verify", __name__)


@verify_bp.route("/verify", methods=["GET", "POST"])
@verify_bp.route("/verify/<path:identifier>", methods=["GET", "POST"])
def verify_certificate(identifier: str | None = None):

    print("👉 PAGE OPEN:", identifier)

    cert = None
    if identifier:
        if identifier.isdigit():
            cert = get_certificate_by_id(int(identifier))
        if not cert:
            cert = get_certificate_by_cid(identifier)

    trust_score = None
    heatmap_path = None
    blockchain_tx = None
    status = None
    error = None

    if not cert:
        error = "Certificate not found."
        cid = None
        blockchain_verified = False
        chain_valid = False
    else:
        cid = cert.cid
        chain_valid = validate_chain()
        block = find_block_by_cid(cid) if cid else None
        blockchain_verified = bool(block and chain_valid)
        blockchain_tx = getattr(cert, "blockchain_tx", None)

        if blockchain_verified:
            pdf_path = FINAL_UPLOAD_DIR / cert.pdf_filename
            if pdf_path.exists():
                try:
                    current_hash = hash_file_sha256(str(pdf_path))
                    blockchain_verified = current_hash == block.certificate_hash
                except Exception as exc:
                    print("❌ Hash compare failed:", exc)
                    blockchain_verified = False
            else:
                blockchain_verified = False

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
                upload_path = TEMP_UPLOAD_DIR / f"verify_{cert.id}_{filename}"

                uploaded_file.save(upload_path)
                print("📁 Saved to:", upload_path)
                print("Upload exists:", upload_path.exists())

                processing_image_path = str(upload_path)
                if filename.lower().endswith(".pdf"):
                    print("📄 PDF conversion started for file:", upload_path)
                    try:
                        converted_path = convert_pdf_to_image(str(upload_path), TEMP_UPLOAD_DIR)
                        processing_image_path = str(converted_path)
                        print("📄 PDF converted to image:", processing_image_path)
                    except Exception as exc:
                        print("❌ PDF conversion failed:", exc)
                        flash("PDF conversion failed. Please check system setup.", "danger")
                        return render_template(
                            "verify.html",
                            identifier=identifier,
                            cid=cid,
                            blockchain_verified=blockchain_verified,
                            chain_valid=chain_valid,
                            certificate=cert,
                            trust_score=trust_score,
                            heatmap_path=heatmap_path,
                            blockchain_tx=blockchain_tx,
                            status=status,
                            error=error,
                        )

                print("FINAL_UPLOAD_DIR:", FINAL_UPLOAD_DIR)
                # Use image_data from DB instead of file
                if cert.image_data:
                    original_image_path = TEMP_UPLOAD_DIR / f"original_{cert.id}.png"
                    with original_image_path.open("wb") as f:
                        f.write(cert.image_data)
                else:
                    original_image_path = FINAL_UPLOAD_DIR / cert.image_filename

                print("Original path:", original_image_path)
                print("Original str path:", str(original_image_path))
                print("Exists:", original_image_path.exists())

                try:
                    status = "Authentic" if blockchain_verified else "Tampered"
                    trust_score = 95 if blockchain_verified else 60

                    print("Calling compare_certificates with:", str(original_image_path), processing_image_path)
                    trust_score, heatmap_rel = compare_certificates(
                        str(original_image_path),
                        processing_image_path,
                        blockchain_verified=blockchain_verified,
                    )

                    heatmap_path = heatmap_rel
                    print("🔥 AI RESULT:", trust_score)
                    print("📝 STATUS:", status)

                except Exception as exc:
                    print("❌ AI ERROR:", exc)
                    flash(f"Verification failed: {exc}", "danger")

    return render_template(
        "verify.html",
        identifier=identifier,
        cid=cid,
        blockchain_verified=blockchain_verified,
        chain_valid=chain_valid,
        certificate=cert,
        trust_score=trust_score,
        heatmap_path=heatmap_path,
        blockchain_tx=blockchain_tx,
        status=status,
        error=error,
    )