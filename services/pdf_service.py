import uuid
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from config import TEMP_UPLOAD_DIR, FINAL_UPLOAD_DIR


def _ensure_dirs() -> None:
    TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def create_temp_certificate_pdf(
    student_name: str,
    register_number: str,
    degree: str,
    department: str,
    year: str,
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
    width, height = 1700, 1200
    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)

    serif_fonts = ["Times New Roman.ttf", "Georgia.ttf", "Times.ttf", "LiberationSerif-Regular.ttf", "DejaVuSerif.ttf"]

    def _load_serif_font(size: int) -> ImageFont.FreeTypeFont:
        for font_name in serif_fonts:
            try:
                return ImageFont.truetype(font_name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    title_font = _load_serif_font(28)
    subtitle_font = _load_serif_font(38)
    body_font = _load_serif_font(30)
    highlight_font = _load_serif_font(38)
    name_font = _load_serif_font(64)
    footer_font = _load_serif_font(24)

    margin = 80
    accent_color = (15, 23, 42)
    subtle_color = (88, 100, 123)

    title_text = "ABC Certificate Verification System"
    subtitle_text = "CERTIFICATE OF COMPLETION"
    intro_text = "This is to certify that"
    name_text = student_name
    detail_line_1 = f"bearing Register Number {register_number}"
    detail_line_2 = "has successfully completed the degree of"
    degree_text = degree
    department_line = "in the Department of"
    department_text = department
    year_line = "in the year"
    year_text = year
    date_text = f"Date: {issue_date}"

    content_lines = [
        (title_text, title_font, subtle_color, 0.9),
        (subtitle_text, subtitle_font, accent_color, 1.8),
        (intro_text, body_font, subtle_color, 1.8),
        (name_text, name_font, accent_color, 1.4),
        (detail_line_1, body_font, subtle_color, 1.3),
        (detail_line_2, body_font, subtle_color, 1.8),
        (degree_text, highlight_font, accent_color, 1.4),
        (department_line, body_font, subtle_color, 1.3),
        (department_text, highlight_font, accent_color, 1.8),
        (year_line, body_font, subtle_color, 1.2),
        (year_text, highlight_font, accent_color, 0.0),
    ]

    total_height = 0
    line_heights = []
    for text, font, _, spacing in content_lines:
        bbox = draw.textbbox((0, 0), text, font=font)
        line_height = bbox[3] - bbox[1]
        line_heights.append((text, font, line_height, spacing))
        total_height += line_height
        total_height += int(line_height * spacing)

    current_y = max(margin, int((height - total_height) / 2))

    for text, font, line_height, spacing in line_heights:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) / 2, current_y), text, fill=accent_color if font in (subtitle_font, name_font, highlight_font) else subtle_color, font=font)
        current_y += line_height + int(line_height * spacing)

    footer_y = height - margin - 90
    left_x = margin

    draw.text((left_x, footer_y), date_text, fill=subtle_color, font=footer_font)

    footer_y = height - margin - 110
    left_x = margin + 50

    draw.text((left_x, footer_y), date_text, fill=subtle_color, font=footer_font)

    image.save(image_path)

    # Render image into a PDF page using ReportLab
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    page_width, page_height = A4
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
    verify_url: str | None = None,
) -> Tuple[Path, Path]:
    """
    STEP 6 & 7: Embed QR into the certificate image and generate final PDF.

    Returns (final_pdf_path, final_image_path).
    """
    _ensure_dirs()
    base_img = Image.open(base_image_path).convert("RGB")
    qr_img = Image.open(qr_image_path).convert("RGB")

    # Resize QR to fit nicely at bottom-right
    qr_size = int(min(base_img.size) * 0.21)
    qr_img = qr_img.resize((qr_size, qr_size))

    margin = 60
    pos = (base_img.width - qr_size - margin, base_img.height - qr_size - margin)
    base_img.paste(qr_img, pos)

    if verify_url:
        draw = ImageDraw.Draw(base_img)
        try:
            font = ImageFont.truetype("Times New Roman.ttf", 24)
        except Exception:
            font = ImageFont.load_default()

        line1 = "Scan QR or verify at:"
        line2 = verify_url
        text_y = pos[1] + qr_size + 18
        bbox = draw.textbbox((0, 0), line1, font=font)
        draw.text((pos[0] + (qr_size - (bbox[2] - bbox[0])) / 2, text_y), line1, fill=(55, 65, 81), font=font)
        text_y += bbox[3] - bbox[1] + 8
        bbox = draw.textbbox((0, 0), line2, font=font)
        draw.text((pos[0] + (qr_size - (bbox[2] - bbox[0])) / 2, text_y), line2, fill=(31, 41, 55), font=font)

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

    if verify_url:
        font_name = "Helvetica"
        font_size = 12
        line_height = font_size * 1.2
        line1 = "Scan QR or verify at:"
        line2 = verify_url

        line1_width = pdfmetrics.stringWidth(line1, font_name, font_size)
        line2_width = pdfmetrics.stringWidth(line2, font_name, font_size)
        text_x = pos[0] + (qr_size - max(line1_width, line2_width)) / 2
        text_y = pos[1] + qr_size + 18
        link_top = y_pos + draw_height - (text_y * (draw_height / height))
        link_bottom = link_top - (line_height * (draw_height / height)) * 2
        link_left = x + text_x * (draw_width / width)
        link_right = x + (text_x + max(line1_width, line2_width)) * (draw_width / width)

        c.linkURL(
            verify_url,
            (link_left, link_bottom, link_right, link_top),
            relative=0,
            thickness=0,
            color=None,
        )

    c.showPage()
    c.save()

    return final_pdf_path, final_image_path

