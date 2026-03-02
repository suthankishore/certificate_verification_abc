import uuid
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from config import TEMP_UPLOAD_DIR, FINAL_UPLOAD_DIR


def _ensure_dirs() -> None:
    TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def create_temp_certificate_pdf(
    student_name: str,
    register_number: str,
    course: str,
    issue_date: str,
) -> Tuple[Path, Path]:
    """
    STEP 1: Generate a temporary certificate PDF and its backing image.

    Returns (temp_pdf_path, base_image_path).
    """
    _ensure_dirs()
    identifier = uuid.uuid4().hex
    image_path = TEMP_UPLOAD_DIR / f"cert_{identifier}.png"
    pdf_path = TEMP_UPLOAD_DIR / f"cert_{identifier}.pdf"

    # Create a clean white certificate image using Pillow
    width, height = 1654, 1169  # ~ A4 at 150 DPI
    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)

    # Basic fonts; fall back to default if custom fails
    try:
        title_font = ImageFont.truetype("arial.ttf", 48)
        body_font = ImageFont.truetype("arial.ttf", 32)
    except Exception:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

    title_text = "Certificate of Completion"
    subtitle_text = "This is to certify that"
    name_text = student_name
    details_text = f"Register No: {register_number}"
    course_text = f"has successfully completed the course: {course}"
    date_text = f"Issue Date: {issue_date}"

    # Centered layout
    y = 150
    for text, font in [
        (title_text, title_font),
        ("", body_font),
        (subtitle_text, body_font),
        (name_text, title_font),
        (details_text, body_font),
        (course_text, body_font),
        (date_text, body_font),
    ]:
        if text:
            # Use textbbox for reliable text measurement across Pillow versions
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text(((width - tw) / 2, y), text, fill="black", font=font)
        y += 80

    image.save(image_path)

    # Render image into a PDF page using ReportLab
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    page_width, page_height = A4
    # Keep aspect ratio
    img_ratio = width / height
    max_width = page_width - 80
    max_height = page_height - 80
    if max_width / max_height > img_ratio:
        draw_height = max_height
        draw_width = draw_height * img_ratio
    else:
        draw_width = max_width
        draw_height = draw_width / img_ratio
    x = (page_width - draw_width) / 2
    y_pos = (page_height - draw_height) / 2
    c.drawImage(str(image_path), x, y_pos, draw_width, draw_height)
    c.showPage()
    c.save()

    return pdf_path, image_path


def embed_qr_and_create_final_pdf(
    base_image_path: Path,
    qr_image_path: Path,
) -> Tuple[Path, Path]:
    """
    STEP 6 & 7: Embed QR into the certificate image and generate final PDF.

    Returns (final_pdf_path, final_image_path).
    """
    _ensure_dirs()
    base_img = Image.open(base_image_path).convert("RGB")
    qr_img = Image.open(qr_image_path).convert("RGB")

    # Resize QR to fit nicely at bottom-right
    qr_size = int(min(base_img.size) * 0.25)
    qr_img = qr_img.resize((qr_size, qr_size))

    margin = 40
    pos = (base_img.width - qr_size - margin, base_img.height - qr_size - margin)
    base_img.paste(qr_img, pos)

    identifier = uuid.uuid4().hex
    final_image_path = FINAL_UPLOAD_DIR / f"cert_final_{identifier}.png"
    final_pdf_path = FINAL_UPLOAD_DIR / f"cert_final_{identifier}.pdf"

    base_img.save(final_image_path)

    # Create final PDF with QR-embedded image
    c = canvas.Canvas(str(final_pdf_path), pagesize=A4)
    page_width, page_height = A4
    width, height = base_img.size
    img_ratio = width / height
    max_width = page_width - 80
    max_height = page_height - 80
    if max_width / max_height > img_ratio:
        draw_height = max_height
        draw_width = draw_height * img_ratio
    else:
        draw_width = max_width
        draw_height = draw_width / img_ratio
    x = (page_width - draw_width) / 2
    y_pos = (page_height - draw_height) / 2
    c.drawImage(str(final_image_path), x, y_pos, draw_width, draw_height)
    c.showPage()
    c.save()

    return final_pdf_path, final_image_path

