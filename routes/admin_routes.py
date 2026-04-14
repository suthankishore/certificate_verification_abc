from collections import Counter
from datetime import datetime, date
from pathlib import Path
import re

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

from config import ADMIN_EMAIL, ADMIN_PASSWORD
from models.certificate_model import get_all_certificates, get_certificate_by_id
from services.blockchain_service import issue_certificate_workflow
from services.email_service import send_certificate_email


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _require_admin() -> bool:
    return session.get("admin_logged_in", False)


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin.dashboard"))
        flash("Invalid admin email or password", "danger")
    return render_template("admin_login.html")


@admin_bp.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.login"))


@admin_bp.route("/dashboard")
def dashboard():
    if not _require_admin():
        return redirect(url_for("admin.login"))

    certificates = get_all_certificates()
    total_certificates = len(certificates)
    issued_today = 0
    verified_certificates = 0
    today = datetime.utcnow().date()

    monthly_counts = Counter()
    for cert in certificates:
        if cert.cid:
            verified_certificates += 1

        try:
            issued_at = datetime.fromisoformat(cert.created_at)
            monthly_counts[issued_at.strftime("%b %Y")] += 1
            if issued_at.date() == today:
                issued_today += 1
        except Exception:
            continue

    if monthly_counts:
        sorted_months = sorted(
            monthly_counts.items(),
            key=lambda item: datetime.strptime(item[0], "%b %Y"),
        )
        graph_labels = [label for label, _ in sorted_months]
        graph_values = [count for _, count in sorted_months]
    else:
        graph_labels = ["No data"]
        graph_values = [0]

    max_value = max(graph_values) if graph_values else 1
    recent_activity = certificates[:5]

    return render_template(
        "admin_dashboard.html",
        total_certificates=total_certificates,
        issued_today=issued_today,
        verified_certificates=verified_certificates,
        graph_labels=graph_labels,
        graph_values=graph_values,
        max_value=max_value,
        recent_activity=recent_activity,
    )


def _is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


@admin_bp.route("/issue", methods=["GET", "POST"])
def issue_certificate():
    if not _require_admin():
        return redirect(url_for("admin.login"))

    form_data = {
        "student_name": "",
        "register_number": "",
        "degree": "",
        "department": "",
        "year": "",
        "issue_date": "",
        "student_email": "",
    }

    if request.method == "POST":
        form_data.update(
            {
                "student_name": request.form.get("student_name", "").strip(),
                "register_number": request.form.get("register_number", "").strip(),
                "degree": request.form.get("degree", "").strip(),
                "department": request.form.get("department", "").strip(),
                "year": request.form.get("year", "").strip(),
                "issue_date": request.form.get("issue_date", "").strip(),
                "student_email": request.form.get("student_email", "").strip(),
            }
        )

        if not all([
            form_data["student_name"],
            form_data["register_number"],
            form_data["degree"],
            form_data["department"],
            form_data["year"],
            form_data["issue_date"],
            form_data["student_email"],
        ]):
            flash("All fields are required.", "danger")
            return render_template("issue_form.html", form_data=form_data)

        if not form_data["year"].isdigit() or len(form_data["year"]) != 4:
            flash("Year of Passing must be a 4-digit number.", "danger")
            return render_template("issue_form.html", form_data=form_data)

        if not _is_valid_email(form_data["student_email"]):
            flash("Please enter a valid student email address.", "danger")
            return render_template("issue_form.html", form_data=form_data)

        try:
            result = issue_certificate_workflow(
                student_name=form_data["student_name"],
                register_number=form_data["register_number"],
                degree=form_data["degree"],
                department=form_data["department"],
                year=form_data["year"],
                issue_date=form_data["issue_date"],
                student_email=form_data["student_email"],
            )
        except Exception as exc:  # pragma: no cover - defensive
            flash(f"Error issuing certificate: {exc}", "danger")
            return render_template("issue_form.html", form_data=form_data)

        try:
            send_certificate_email(
                to_email=form_data["student_email"],
                student_name=form_data["student_name"],
                subject="Your Certificate Has Been Issued",
                body=(
                    "Dear Student,\n\n"
                    "We are pleased to inform you that your certificate has been successfully issued through the ABC Certificate Verification System.\n\n"
                    "Please find your certificate attached with this email. You can open and download the certificate directly on your device.\n\n"
                    "The certificate includes a QR code for verification and authenticity checking.\n\n"
                    "If you have any questions or require assistance, please contact the issuing authority.\n\n"
                    "Best regards,\n"
                    "ABC Certificate Verification System"
                ),
                attachment_path=result["final_pdf_path"],
            )
            flash("Certificate generated and sent successfully to the student email.", "success")
        except Exception:
            flash(
                "Certificate generated successfully, but the provided email is not valid or email delivery failed.",
                "danger",
            )

        return render_template(
            "preview.html",
            student_name=form_data["student_name"],
            register_number=form_data["register_number"],
            degree=form_data["degree"],
            department=form_data["department"],
            year=form_data["year"],
            issue_date=form_data["issue_date"],
            certificate_id=result["certificate_id"],
            verify_url=result.get("verify_url"),
            final_pdf_filename=Path(result["final_pdf_path"]).name,
            final_image_filename=Path(result["final_image_path"]).name,
        )

    return render_template("issue_form.html", form_data=form_data)


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
    course_options = sorted({cert.course for cert in certs if cert.course})
    return render_template(
        "issued_list.html",
        certificates=certs,
        student_view=False,
        course_options=course_options,
    )


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


