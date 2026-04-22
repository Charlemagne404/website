import os
import re
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename

from content_store import (
    add_admin_email,
    get_admin_emails,
    list_content_backups,
    get_site_content,
    normalize_email,
    remove_admin_email,
    restore_site_content,
    save_site_content,
)


BASE_DIR = Path(__file__).resolve().parent
DOCUMENT_YEAR_PATTERN = re.compile(r"^\d{4}$")


def parse_bool(value, default=False):
    if value is None:
        return default

    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def parse_csv(value):
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def create_app(test_config=None):
    environment = str(os.environ.get("APP_ENV", "development")).strip().lower() or "development"
    default_secret = None if environment == "production" else "development-secret"
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.update(
        APP_ENV=environment,
        SECRET_KEY=os.environ.get("SECRET_KEY", default_secret),
        CONTENT_PATH=BASE_DIR / "data" / "site-content.json",
        ADMINS_PATH=BASE_DIR / "data" / "admins.json",
        INITIAL_ADMIN_EMAILS=os.environ.get("INITIAL_ADMIN_EMAILS", ""),
        GOOGLE_CLIENT_ID=os.environ.get("GOOGLE_CLIENT_ID", ""),
        GOOGLE_HOSTED_DOMAIN=os.environ.get("GOOGLE_HOSTED_DOMAIN", ""),
        DOCUMENTS_FOLDER=BASE_DIR / "static" / "documents",
        BACKUPS_DIR=BASE_DIR / "data" / "backups",
        BACKUP_KEEP_COUNT=int(os.environ.get("BACKUP_KEEP_COUNT", "25")),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,
        MAX_FORM_MEMORY_SIZE=16 * 1024 * 1024,
        PREFERRED_URL_SCHEME=os.environ.get(
            "PREFERRED_URL_SCHEME",
            "https" if environment == "production" else "http",
        ),
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=parse_bool(
            os.environ.get("SESSION_COOKIE_SECURE"),
            default=environment == "production",
        ),
        TRUST_PROXY_HEADERS=parse_bool(os.environ.get("TRUST_PROXY_HEADERS"), default=False),
        TRUSTED_HOSTS=parse_csv(os.environ.get("TRUSTED_HOSTS", "")) or None,
    )

    if test_config:
        app.config.update(test_config)

    if app.config.get("TRUST_PROXY_HEADERS"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    if (
        app.config.get("APP_ENV") == "production"
        and not app.config.get("TESTING")
        and app.config.get("SECRET_KEY") in {None, "", "development-secret"}
    ):
        raise RuntimeError("SECRET_KEY must be set to a strong value when APP_ENV=production")

    def seeded_admins():
        raw_emails = app.config.get("INITIAL_ADMIN_EMAILS", "")
        return [email.strip() for email in str(raw_emails).split(",") if email.strip()]

    get_site_content(app.config["CONTENT_PATH"])
    get_admin_emails(app.config["ADMINS_PATH"], seeded_admins())

    def current_admin():
        email = normalize_email(session.get("admin_email"))
        if not email:
            return None

        allowed = set(get_admin_emails(app.config["ADMINS_PATH"], seeded_admins()))
        if email not in allowed:
            session.clear()
            return None

        return {
            "email": email,
            "name": session.get("admin_name", email),
            "picture": session.get("admin_picture", ""),
        }

    def login_required(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if not current_admin():
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Unauthorized"}), 401
                return redirect(url_for("admin_login"))
            return view(*args, **kwargs)

        return wrapped_view

    def verify_google_credential(credential):
        verifier = app.config.get("VERIFY_GOOGLE_TOKEN_FUNC")
        if verifier:
            return verifier(credential)

        client_id = app.config.get("GOOGLE_CLIENT_ID")
        if not client_id:
            raise ValueError("GOOGLE_CLIENT_ID is not configured")

        return id_token.verify_oauth2_token(credential, GoogleRequest(), client_id)

    def validate_admin_identity(payload):
        credential = str(payload.get("credential", "")).strip()
        if not credential:
            abort(400, "Missing Google credential")

        identity = verify_google_credential(credential)
        email = normalize_email(identity.get("email"))
        email_verified = bool(identity.get("email_verified"))
        hosted_domain = str(identity.get("hd", "")).strip()

        if not email or not email_verified:
            abort(401, "Google account email is not verified")

        required_domain = str(app.config.get("GOOGLE_HOSTED_DOMAIN", "")).strip()
        if required_domain and hosted_domain != required_domain:
            abort(403, "Google account is not part of the allowed domain")

        allowed_admins = set(get_admin_emails(app.config["ADMINS_PATH"], seeded_admins()))
        if email not in allowed_admins:
            abort(403, "This Google account is not allowed to manage the website")

        return {
            "email": email,
            "name": identity.get("name") or email,
            "picture": identity.get("picture") or "",
        }

    def json_payload():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            abort(400, "Request body must be a JSON object")
        return payload

    def public_content():
        return get_site_content(app.config["CONTENT_PATH"])

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": error.description}), error.code
        return error

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), geolocation=(), microphone=()",
        )

        if (
            request.path.startswith("/admin")
            or request.path.startswith("/api/admin/")
            or request.path.startswith("/api/auth/")
            or request.path == "/healthz"
        ):
            response.headers.setdefault("Cache-Control", "no-store")

        return response

    @app.context_processor
    def inject_helpers():
        def format_public_timestamp(value):
            if not value:
                return ""

            try:
                parsed = datetime.fromisoformat(value)
            except ValueError:
                return value

            month_names = [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ]
            month_name = month_names[parsed.month - 1]
            return f"{parsed.day} {month_name}, {parsed.year}"

        return {"format_public_timestamp": format_public_timestamp}

    @app.route("/")
    def index():
        return render_template("index.html", content=public_content())

    @app.route("/favicon.png")
    def favicon():
        return app.send_static_file("favicon.png")

    @app.get("/healthz")
    def healthcheck():
        return jsonify({"ok": True})

    @app.route("/documents/<path:filename>")
    def document_file(filename):
        return send_from_directory(app.config["DOCUMENTS_FOLDER"], filename, conditional=True)

    @app.route("/admin/login")
    def admin_login():
        if current_admin():
            return redirect(url_for("admin"))

        return render_template(
            "admin_login.html",
            google_client_id=app.config.get("GOOGLE_CLIENT_ID", ""),
            hosted_domain=app.config.get("GOOGLE_HOSTED_DOMAIN", ""),
        )

    @app.route("/admin")
    @login_required
    def admin():
        return render_template(
            "admin.html",
            admin=current_admin(),
            public_url=url_for("index"),
        )

    @app.post("/admin/logout")
    @login_required
    def admin_logout():
        session.clear()
        return redirect(url_for("admin_login"))

    @app.post("/api/auth/google")
    def admin_google_login():
        identity = validate_admin_identity(json_payload())
        session["admin_email"] = identity["email"]
        session["admin_name"] = identity["name"]
        session["admin_picture"] = identity["picture"]
        return jsonify({"ok": True, "admin": identity})

    @app.get("/api/admin/session")
    @login_required
    def admin_session():
        return jsonify({"admin": current_admin()})

    @app.get("/api/content")
    def site_content():
        return jsonify(public_content())

    @app.get("/api/admin/content")
    @login_required
    def admin_content():
        return jsonify(public_content())

    @app.put("/api/admin/content")
    @login_required
    def update_content():
        content = json_payload()
        admin_user = current_admin()
        content["meta"] = content.get("meta", {})
        content["meta"]["updated_at"] = datetime.now().astimezone().isoformat()
        content["meta"]["updated_by_name"] = admin_user["name"]
        content["meta"]["updated_by_email"] = admin_user["email"]

        saved = save_site_content(
            app.config["CONTENT_PATH"],
            content,
            backups_dir=app.config["BACKUPS_DIR"],
            actor_name=admin_user["name"],
            actor_email=admin_user["email"],
            backup_reason="save",
            backup_keep=app.config["BACKUP_KEEP_COUNT"],
        )
        return jsonify({"ok": True, "content": saved})

    @app.get("/api/admin/history")
    @login_required
    def content_history():
        return jsonify(
            {
                "items": list_content_backups(
                    app.config["BACKUPS_DIR"],
                    limit=app.config["BACKUP_KEEP_COUNT"],
                )
            }
        )

    @app.post("/api/admin/history/restore")
    @login_required
    def restore_content_history():
        payload = json_payload()
        backup_id = str(payload.get("backup_id", "")).strip()
        if not backup_id:
            abort(400, "Missing backup_id")

        admin_user = current_admin()

        try:
            restored = restore_site_content(
                app.config["CONTENT_PATH"],
                app.config["BACKUPS_DIR"],
                backup_id,
                actor_name=admin_user["name"],
                actor_email=admin_user["email"],
                backup_keep=app.config["BACKUP_KEEP_COUNT"],
            )
        except FileNotFoundError:
            abort(404, "Backup not found")

        restored["meta"] = restored.get("meta", {})
        restored["meta"]["updated_at"] = datetime.now().astimezone().isoformat()
        restored["meta"]["updated_by_name"] = admin_user["name"]
        restored["meta"]["updated_by_email"] = admin_user["email"]
        restored = save_site_content(
            app.config["CONTENT_PATH"],
            restored,
            backups_dir=None,
        )

        return jsonify({"ok": True, "content": restored})

    @app.get("/api/admin/admins")
    @login_required
    def list_admins():
        return jsonify({"emails": get_admin_emails(app.config["ADMINS_PATH"], seeded_admins())})

    @app.post("/api/admin/admins")
    @login_required
    def create_admin():
        payload = json_payload()
        try:
            emails = add_admin_email(app.config["ADMINS_PATH"], payload.get("email"))
        except ValueError as error:
            abort(400, str(error))

        return jsonify({"ok": True, "emails": emails})

    @app.delete("/api/admin/admins")
    @login_required
    def delete_admin():
        payload = json_payload()
        try:
            emails = remove_admin_email(app.config["ADMINS_PATH"], payload.get("email"))
        except KeyError:
            abort(404, "Admin account not found")
        except RuntimeError as error:
            abort(400, str(error))

        if normalize_email(payload.get("email")) == normalize_email(session.get("admin_email")):
            session.clear()

        return jsonify({"ok": True, "emails": emails})

    @app.post("/api/admin/uploads/documents")
    @login_required
    def upload_document():
        if "file" not in request.files:
            abort(400, "Missing file upload")

        uploaded_file = request.files["file"]
        year = str(request.form.get("year", "")).strip()

        if not uploaded_file.filename:
            abort(400, "Missing filename")

        if not year:
            abort(400, "Missing year")

        if not DOCUMENT_YEAR_PATTERN.fullmatch(year):
            abort(400, "Year must use four digits")

        filename = secure_filename(uploaded_file.filename)
        if not filename.lower().endswith(".pdf"):
            abort(400, "Only PDF uploads are supported")

        if not filename:
            abort(400, "Invalid filename")

        header = uploaded_file.stream.read(5)
        uploaded_file.stream.seek(0)
        if header != b"%PDF-":
            abort(400, "Uploaded file is not a valid PDF")

        destination = Path(app.config["DOCUMENTS_FOLDER"]) / year
        destination.mkdir(parents=True, exist_ok=True)

        filepath = destination / filename
        uploaded_file.save(filepath)

        return jsonify({"ok": True, "url": f"/documents/{year}/{filename}"})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("FLASK_RUN_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=parse_bool(os.environ.get("FLASK_DEBUG"), default=False),
    )
