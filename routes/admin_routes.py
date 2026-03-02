from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory,
)

from config import ADMIN_USERNAME, ADMIN_PASSWORD
from models.certificate_model import get_all_certificates, get_certificate_by_id
from services.blockchain_service import issue_certificate_workflow


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _require_admin() -> bool:
    return session.get("admin_logged_in", False)


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin.dashboard"))
        flash("Invalid admin credentials", "danger")
    return render_template("admin_login.html")


@admin_bp.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.login"))


@admin_bp.route("/dashboard")
def dashboard():
    if not _require_admin():
        return redirect(url_for("admin.login"))
    return render_template("admin_dashboard.html")


@admin_bp.route("/issue", methods=["GET", "POST"])
def issue_certificate():
    if not _require_admin():
        return redirect(url_for("admin.login"))

    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        register_number = request.form.get("register_number", "").strip()
        course = request.form.get("course", "").strip()
        issue_date = request.form.get("issue_date", "").strip()

        if not all([student_name, register_number, course, issue_date]):
            flash("All fields are required.", "danger")
            return render_template("issue_form.html")

        try:
            result = issue_certificate_workflow(
                student_name=student_name,
                register_number=register_number,
                course=course,
                issue_date=issue_date,
            )
        except Exception as exc:  # pragma: no cover - defensive
            flash(f"Error issuing certificate: {exc}", "danger")
            return render_template("issue_form.html")

        # Preview page: show only the final certificate (no blockchain/AI details)
        return render_template(
            "preview.html",
            student_name=student_name,
            register_number=register_number,
            course=course,
            issue_date=issue_date,
            certificate_id=result["certificate_id"],
            final_pdf_filename=result["final_pdf_path"].split("/")[-1],
            final_image_filename=result["final_image_path"].split("/")[-1],
        )

    return render_template("issue_form.html")


@admin_bp.route("/preview_file/<path:filename>")
def preview_file(filename: str):
    """Serve final uploaded files to the admin (authenticated)."""
    if not _require_admin():
        return redirect(url_for("admin.login"))
    # FINAL_UPLOAD_DIR is defined in config; import here to avoid circulars
    from config import FINAL_UPLOAD_DIR

    return send_from_directory(str(FINAL_UPLOAD_DIR), filename, as_attachment=False)


@admin_bp.route("/download_file/<path:filename>")
def download_file(filename: str):
    """Allow admin to download final assets."""
    if not _require_admin():
        return redirect(url_for("admin.login"))
    from config import FINAL_UPLOAD_DIR

    return send_from_directory(str(FINAL_UPLOAD_DIR), filename, as_attachment=True)


@admin_bp.route("/issued")
def issued_certificates():
    if not _require_admin():
        return redirect(url_for("admin.login"))
    certs = get_all_certificates()
    return render_template("issued_list.html", certificates=certs)


@admin_bp.route("/certificate/view/<int:cert_id>")
def view_certificate(cert_id: int):
    """Allow admin to view a certificate's details, student info, and QR code."""
    if not _require_admin():
        return redirect(url_for("admin.login"))
    
    cert = get_certificate_by_id(cert_id)
    if not cert:
        flash("Certificate not found.", "danger")
        return redirect(url_for("admin.issued_certificates"))
    
    return render_template(
        "admin_certificate_view.html",
        certificate=cert,
    )


