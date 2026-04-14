import cv2
import numpy as np
import fitz
import uuid
from pathlib import Path

from config import HEATMAP_DIR


def _ensure_heatmap_dir() -> None:
    HEATMAP_DIR.mkdir(parents=True, exist_ok=True)


def _save_heatmap(heatmap: np.ndarray) -> str:
    _ensure_heatmap_dir()
    output_filename = f"heatmap_{uuid.uuid4().hex}.png"
    output_path = HEATMAP_DIR / output_filename
    cv2.imwrite(str(output_path), heatmap)
    return f"heatmaps/{output_filename}"


def compare_certificates(orig_image, uploaded_image, blockchain_verified: bool = False):
    if not hasattr(orig_image, "shape"):
        orig = cv2.imread(str(orig_image))
    else:
        orig = orig_image

    if orig is None:
        raise FileNotFoundError(f"Original image not found: {orig_image}")

    if not hasattr(uploaded_image, "shape"):
        uploaded = cv2.imread(str(uploaded_image))
    else:
        uploaded = uploaded_image

    if uploaded is None:
        raise FileNotFoundError(f"Uploaded image not found: {uploaded_image}")

    uploaded = cv2.resize(uploaded, (orig.shape[1], orig.shape[0]), interpolation=cv2.INTER_AREA)

    heatmap = np.zeros_like(orig)
    heatmap[:] = (0, 255, 0)

    trust_score = 95 if blockchain_verified else 60

    orig_gray = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
    uploaded_gray = cv2.cvtColor(uploaded, cv2.COLOR_BGR2GRAY)

    h, w = orig_gray.shape
    x1, x2 = int(w * 0.10), int(w * 0.90)
    y1, y2 = int(h * 0.20), int(h * 0.70)

    roi1 = orig_gray[y1:y2, x1:x2]
    roi2 = uploaded_gray[y1:y2, x1:x2]

    diff = cv2.absdiff(roi1, roi2)
    diff = cv2.GaussianBlur(diff, (5, 5), 0)

    if np.mean(diff) < 10:
        return trust_score, _save_heatmap(heatmap)

    _, mask = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    region = heatmap[y1:y2, x1:x2]
    region[mask == 255] = (0, 0, 255)

    return trust_score, _save_heatmap(heatmap)


def convert_pdf_to_image(pdf_path: str, output_dir: Path) -> Path:
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
    output_path = output_dir / f"converted_{Path(pdf_path).stem}.png"
    pix.save(str(output_path))
    return output_path