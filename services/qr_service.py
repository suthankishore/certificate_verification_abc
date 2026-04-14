from pathlib import Path
import re
from urllib.parse import urlparse, parse_qs

import qrcode
import cv2

from config import BASE_URL, QR_DIR


def extract_cid_from_qr_image(image_path: str) -> str | None:
    """Detect and extract CID or certificate URL from QR code image."""
    # opencv QR decoder can handle standard QR code images
    detector = cv2.QRCodeDetector()
    image = cv2.imread(str(image_path))
    if image is None:
        return None

    data, points, _ = detector.detectAndDecode(image)
    if not data:
        return None

    # If we got a URL containing /verify/<id>, we ignore in favor of direct CID.
    data = data.strip()

    # Direct CID only
    if re.fullmatch(r"[A-Za-z0-9]{10,}$", data):
        return data

    # URL with query or path
    try:
        parsed = urlparse(data)
    except Exception:
        return None

    # If query has cid parameter
    query_vals = parse_qs(parsed.query)
    if "cid" in query_vals and query_vals["cid"]:
        return query_vals["cid"][0]

    # Path contains /verify/<id> or /cid/<cid>
    match = re.search(r"/verify/(\d+)", parsed.path)
    if match:
        return match.group(1)  # return certificate_id

    match = re.search(r"/cid/([A-Za-z0-9]{10,})", parsed.path)
    if match:
        return match.group(1)

    return None


def build_verification_url(certificate_id: int, cid: str | None = None) -> str:
    """
    Build the verification URL used for QR generation and certificate text.
    """
    # Normalize base URL and ensure proper scheme
    base = BASE_URL.strip().rstrip('/')

    from config import USE_HTTPS

    if (
        not base
        or 'yourdomain.com' in base.lower()
        or base.startswith('http://127.0.0.1')
        or base.startswith('https://127.0.0.1')
        or base.startswith('http://localhost')
        or base.startswith('https://localhost')
    ):
        if not USE_HTTPS:
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            except Exception:  # pragma: no cover - best effort
                local_ip = "127.0.0.1"
            finally:
                try:
                    s.close()
                except Exception:
                    pass

            base = f"http://{local_ip}:5000"
        else:
            base = "https://localhost:5000"

    if not base.startswith('http://') and not base.startswith('https://'):
        scheme = 'https' if USE_HTTPS else 'http'
        base = f"{scheme}://{base}"

    verify_path = cid if cid else str(certificate_id)
    return f"{base}/verify/{verify_path}"


def generate_qr_for_certificate_id(certificate_id: int, cid: str | None = None) -> tuple[Path, str]:
    """
    Generate a QR code PNG pointing to the verification endpoint.
    Prefer a CID-based verification link when CID is available.

    Returns the QR image path and the verification URL.
    """
    QR_DIR.mkdir(parents=True, exist_ok=True)
    verify_url = build_verification_url(certificate_id, cid)
    img = qrcode.make(verify_url)
    output_path = QR_DIR / f"cert_{certificate_id}.png"
    img.save(output_path)
    return output_path, verify_url

