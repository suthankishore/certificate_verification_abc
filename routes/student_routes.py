from pathlib import Path

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

from config import STUDENT_PASSWORD, FINAL_UPLOAD_DIR
from models.certificate_model import get_certificates_by_register, get_certificate_by_id


student_bp = Blueprint("student", __name__, url_prefix="/student")


def _require_student() -> str:
    return session.get("student_register", "")


@student_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        register_number = request.form.get("register_number", "").strip()
        password = request.form.get("password", "").strip()

        if password != STUDENT_PASSWORD or not register_number:
            flash("Invalid student credentials", "danger")
            return render_template("student_login.html")

        session["student_register"] = register_number
        return redirect(url_for("student.dashboard"))

    return render_template("student_login.html")


@student_bp.route("/logout")
def logout():
    session.pop("student_register", None)
    return redirect(url_for("student.login"))


@student_bp.route("/dashboard")
def dashboard():
    register_number = _require_student()
    if not register_number:
        return redirect(url_for("student.login"))
    certs = get_certificates_by_register(register_number)
    return render_template("admin_dashboard.html", student_view=True, certificates=certs)


@student_bp.route("/certificates")
def list_certificates():
    register_number = _require_student()
    if not register_number:
        return redirect(url_for("student.login"))
    certs = get_certificates_by_register(register_number)
    return render_template("issued_list.html", certificates=certs, student_view=True)


@student_bp.route("/download/<int:cert_id>")
def download_certificate(cert_id: int):
    register_number = _require_student()
    if not register_number:
        return redirect(url_for("student.login"))

    cert = get_certificate_by_id(cert_id)
    if not cert or cert.register_number != register_number:
        flash("Certificate not found.", "danger")
        return redirect(url_for("student.list_certificates"))

    directory = FINAL_UPLOAD_DIR
    return send_from_directory(
        directory=str(directory),
        path=cert.pdf_filename,
        as_attachment=True,
    )

