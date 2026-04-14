import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

# Flask settings
SECRET_KEY = os.environ.get("ABC_SECRET_KEY", "super-secret-abc-key")
DEBUG = False

# Admin credentials (hardcoded as requested)
ADMIN_EMAIL = os.environ.get("ABC_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("ABC_ADMIN_PASS", "admin123")

# Email delivery configuration
EMAIL_HOST = os.environ.get("ABC_EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("ABC_EMAIL_PORT", "587"))
EMAIL_USER = os.environ.get("ABC_EMAIL_USER", "suthankishore001@gmail.com")
EMAIL_PASSWORD = os.environ.get("ABC_EMAIL_PASSWORD", "msncanxypidimxnu")
EMAIL_FROM = os.environ.get("ABC_EMAIL_FROM", EMAIL_USER)
EMAIL_USE_TLS = os.environ.get("ABC_EMAIL_USE_TLS", "true").lower() in ("1", "true", "yes")
EMAIL_USE_SSL = os.environ.get("ABC_EMAIL_USE_SSL", "false").lower() in ("1", "true", "yes")

# Simple student auth: register number + common password
STUDENT_PASSWORD = os.environ.get("ABC_STUDENT_PASS", "student123")

# Paths
INSTANCE_DIR = BASE_DIR / "instance"
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "database.db"

UPLOAD_ROOT = BASE_DIR / "uploads"
TEMP_UPLOAD_DIR = UPLOAD_ROOT / "temp"
FINAL_UPLOAD_DIR = UPLOAD_ROOT / "final"

STATIC_DIR = BASE_DIR / "static"
QR_DIR = STATIC_DIR / "qr"
HEATMAP_DIR = STATIC_DIR / "heatmaps"

BLOCKCHAIN_DIR = BASE_DIR / "blockchain"
BLOCKCHAIN_PATH = BLOCKCHAIN_DIR / "chain.json"

# Local "IPFS-like" storage (real filesystem-based implementation)
IPFS_STORAGE_DIR = UPLOAD_ROOT / "ipfs"

# Base URL used inside QR codes
# Default should not be localhost; use a placeholder domain. Override via ABC_BASE_URL.
BASE_URL = "http://127.0.0.1:5000"

# SSL/HTTPS Configuration
# For production with a real domain and valid certificate (e.g. Let's Encrypt):
#   export ABC_USE_HTTPS=true
#   export ABC_SSL_CERT=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
#   export ABC_SSL_KEY=/etc/letsencrypt/live/yourdomain.com/privkey.pem
# *Do not* use self-signed certificates in production; they will trigger
# mobile/HR scanners to show certificate errors.
# For local development, use HTTP (leave USE_HTTPS=false) and set BASE_URL
# to something like "192.168.x.x:5000" or "localhost:5000".
USE_HTTPS = os.environ.get("ABC_USE_HTTPS", "false").lower() == "true"
SSL_CERT_PATH = os.environ.get("ABC_SSL_CERT", None)
SSL_KEY_PATH = os.environ.get("ABC_SSL_KEY", None)


def ensure_directories() -> None:
    """
    Ensure that all required directories exist before the app starts.
    """
    for path in [
        INSTANCE_DIR,
        DATABASE_DIR,
        UPLOAD_ROOT,
        TEMP_UPLOAD_DIR,
        FINAL_UPLOAD_DIR,
        STATIC_DIR,
        QR_DIR,
        HEATMAP_DIR,
        BLOCKCHAIN_DIR,
        IPFS_STORAGE_DIR,
    ]:
        os.makedirs(path, exist_ok=True)

