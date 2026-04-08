from flask import Flask, render_template, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from config import (
    SECRET_KEY,
    DEBUG,
    ensure_directories,
    USE_HTTPS,
    SSL_CERT_PATH,
    SSL_KEY_PATH,
)
from database.init_db import init_db
from services.blockchain_service import initialize_blockchain
from routes.admin_routes import admin_bp
from routes.student_routes import student_bp
from routes.verify_routes import verify_bp


def create_app() -> Flask:
    """
    Application factory for the ABC – AI + Blockchain Certificate Verification System.
    """
    ensure_directories()
    init_db()
    initialize_blockchain()

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["DEBUG"] = DEBUG
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Warn developer if configuration might cause QR SSL errors
    # e.g. using a private address with HTTPS enabled will trigger certificate
    # errors when scanning from external devices.
    if USE_HTTPS:
        from config import BASE_URL
        if any(x in BASE_URL for x in ("localhost", "127.0.0.1", "192.168.")):
            import warnings

            warnings.warn(
                f"BASE_URL={BASE_URL!r} is a local/private address while HTTPS is enabled. "
                "QR code scans on mobile devices may fail with SSL errors."
            )

    # Register blueprints
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(verify_bp)

    # Redirect HTTP -> HTTPS if we are running in secure mode
    if USE_HTTPS:
        @app.before_request
        def enforce_https():
            # flask's request is not imported here; import lazily to avoid circular
            from flask import request, redirect

            # some proxies already set X-Forwarded-Proto
            proto = request.headers.get("X-Forwarded-Proto", request.scheme)
            if proto != "https":
                url = request.url.replace("http://", "https://", 1)
                # Preserve POST method and multipart body for upload forms.
                return redirect(url, code=308)

    @app.route("/")
    def index():
        # Simple landing page with Admin / Student login buttons
        return render_template("index.html")

    # Default redirect helpers
    @app.route("/home")
    def home():
        return redirect(url_for("index"))

    return app


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(host="0.0.0.0", port=5000, debug=True)

