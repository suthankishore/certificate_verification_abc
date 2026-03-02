from pathlib import Path
from typing import Tuple

import cv2
import numpy as np

from config import HEATMAP_DIR


def _ensure_dirs() -> None:
    HEATMAP_DIR.mkdir(parents=True, exist_ok=True)


def _resize_to_match(img1: np.ndarray, img2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Resize second image to match first image size.
    """
    h, w = img1.shape[:2]
    resized = cv2.resize(img2, (w, h), interpolation=cv2.INTER_AREA)
    return img1, resized


def compare_certificates(
    original_image_path: str,
    uploaded_image_path: str,
) -> Tuple[float, str]:
    """
    Perform a simple AI-based forgery detection using OpenCV.

    - Convert both images to grayscale.
    - Resize uploaded image to original size.
    - Compute absolute difference and create heatmap.
    - Derive trust score (0-100%) from normalized difference.

    Returns (trust_score, heatmap_relative_path).
    """
    _ensure_dirs()
    orig = cv2.imread(str(original_image_path))
    uploaded = cv2.imread(str(uploaded_image_path))

    if orig is None or uploaded is None:
        raise ValueError("Could not read one of the certificate images for AI comparison.")

    orig_gray = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
    uploaded_gray = cv2.cvtColor(uploaded, cv2.COLOR_BGR2GRAY)

    orig_gray, uploaded_gray = _resize_to_match(orig_gray, uploaded_gray)

    # Absolute difference
    diff = cv2.absdiff(orig_gray, uploaded_gray)
    norm_diff = cv2.normalize(diff.astype("float32"), None, 0.0, 1.0, cv2.NORM_MINMAX)

    # Average difference used to compute trust score
    mean_diff = float(np.mean(norm_diff))
    trust_score = max(0.0, 100.0 * (1.0 - mean_diff))

    # Create heatmap for visualization
    diff_8u = (norm_diff * 255).astype("uint8")
    heatmap_color = cv2.applyColorMap(diff_8u, cv2.COLORMAP_JET)

    heatmap_path = HEATMAP_DIR / f"heatmap_{Path(uploaded_image_path).stem}.png"
    cv2.imwrite(str(heatmap_path), heatmap_color)

    # Return path relative to static directory
    relative_path = f"heatmaps/{heatmap_path.name}"
    return trust_score, relative_path

