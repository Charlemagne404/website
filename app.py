import logging
import os
import re
import time
from collections import defaultdict, deque
from secrets import compare_digest, token_urlsafe
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit
from xml.etree.ElementTree import Element, SubElement, tostring

from flask import Flask, abort, g, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename

from content_validation import ContentValidationError, validate_site_content
from content_store import (
    add_admin_email,
    append_audit_event,
    get_admin_emails,
    list_content_backups,
    get_site_content,
    normalize_email,
    remove_admin_email,
    restore_site_content,
    save_site_content,
)
from default_content import get_default_site_content


BASE_DIR = Path(__file__).resolve().parent
DOCUMENT_YEAR_PATTERN = re.compile(r"^\d{4}$")
CSRF_SESSION_KEY = "_csrf_token"
CSRF_HEADER = "X-CSRF-Token"
REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
DEFAULT_SOCIAL_IMAGE = "social-preview.svg"


def parse_bool(value, default=False):
    if value is None:
        return default

    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def parse_csv(value):
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def path_from_env(value, default):
    if value in {None, ""}:
        return default
    return Path(value).expanduser()


def configure_logging(app):
    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    root_logger.setLevel(level)
    app.logger.setLevel(level)


class InMemoryRateLimiter:
    def __init__(self):
        self._entries = defaultdict(deque)
        self._lock = Lock()

    def allow(self, bucket, key, limit, window_seconds):
        if limit <= 0 or window_seconds <= 0:
            return True, 0

        now = time.time()
        with self._lock:
            timestamps = self._entries[(bucket, key)]
            while timestamps and now - timestamps[0] >= window_seconds:
                timestamps.popleft()

            if len(timestamps) >= limit:
                retry_after = max(1, int(window_seconds - (now - timestamps[0])))
                return False, retry_after

            timestamps.append(now)

        return True, 0


def create_app(test_config=None):
    environment = str(os.environ.get("APP_ENV", "development")).strip().lower() or "development"
    default_secret = None if environment == "production" else "development-secret"
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.update(
        APP_ENV=environment,
        SECRET_KEY=os.environ.get("SECRET_KEY", default_secret),
        CONTENT_PATH=path_from_env(os.environ.get("CONTENT_PATH"), BASE_DIR / "data" / "site-content.json"),
        ADMINS_PATH=path_from_env(os.environ.get("ADMINS_PATH"), BASE_DIR / "data" / "admins.json"),
        INITIAL_ADMIN_EMAILS=os.environ.get("INITIAL_ADMIN_EMAILS", ""),
        GOOGLE_CLIENT_ID=os.environ.get("GOOGLE_CLIENT_ID", ""),
        GOOGLE_HOSTED_DOMAIN=os.environ.get("GOOGLE_HOSTED_DOMAIN", ""),
        DOCUMENTS_FOLDER=path_from_env(os.environ.get("DOCUMENTS_FOLDER"), BASE_DIR / "static" / "documents"),
        BACKUPS_DIR=path_from_env(os.environ.get("BACKUPS_DIR"), BASE_DIR / "data" / "backups"),
        AUDIT_LOG_PATH=path_from_env(os.environ.get("AUDIT_LOG_PATH"), BASE_DIR / "data" / "admin-audit.jsonl"),
        BACKUP_KEEP_COUNT=int(os.environ.get("BACKUP_KEEP_COUNT", "25")),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,
        MAX_FORM_MEMORY_SIZE=16 * 1024 * 1024,
        STATIC_IMMUTABLE_MAX_AGE=31536000,
        STATIC_DEFAULT_MAX_AGE=300,
        PUBLIC_FILE_MAX_AGE=3600,
        SITE_URL=str(os.environ.get("SITE_URL", "")).strip().rstrip("/"),
        SOCIAL_IMAGE_URL=str(os.environ.get("SOCIAL_IMAGE_URL", "")).strip(),
        SITE_TWITTER_HANDLE=str(os.environ.get("SITE_TWITTER_HANDLE", "")).strip(),
        SITE_LOCALE=str(os.environ.get("SITE_LOCALE", "sv_SE")).strip() or "sv_SE",
        LOG_LEVEL=str(os.environ.get("LOG_LEVEL", "INFO")).strip().upper() or "INFO",
        AUTH_RATE_LIMIT_WINDOW_SECONDS=int(os.environ.get("AUTH_RATE_LIMIT_WINDOW_SECONDS", "300")),
        AUTH_RATE_LIMIT_MAX_ATTEMPTS=int(os.environ.get("AUTH_RATE_LIMIT_MAX_ATTEMPTS", "10")),
        ADMIN_MUTATION_RATE_LIMIT_WINDOW_SECONDS=int(
            os.environ.get("ADMIN_MUTATION_RATE_LIMIT_WINDOW_SECONDS", "300")
        ),
        ADMIN_MUTATION_RATE_LIMIT_MAX_REQUESTS=int(
            os.environ.get("ADMIN_MUTATION_RATE_LIMIT_MAX_REQUESTS", "60")
        ),
        ADMIN_SESSION_HOURS=int(os.environ.get("ADMIN_SESSION_HOURS", "12")),
        PREFERRED_URL_SCHEME=os.environ.get(
            "PREFERRED_URL_SCHEME",
            "https" if environment == "production" else "http",
        ),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=int(os.environ.get("ADMIN_SESSION_HOURS", "12"))),
        SESSION_REFRESH_EACH_REQUEST=True,
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

    configure_logging(app)

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

    rate_limiter = InMemoryRateLimiter()

    def ensure_csp_nonce():
        if not getattr(g, "csp_nonce", None):
            g.csp_nonce = token_urlsafe(16)
        return g.csp_nonce

    def csrf_token():
        token = session.get(CSRF_SESSION_KEY)
        if not token:
            token = token_urlsafe(32)
            session[CSRF_SESSION_KEY] = token
        return token

    def asset_url(filename):
        static_file = Path(app.static_folder or BASE_DIR / "static") / filename

        try:
            version = str(static_file.stat().st_mtime_ns)
        except OSError:
            return url_for("static", filename=filename)

        return url_for("static", filename=filename, v=version)

    get_site_content(app.config["CONTENT_PATH"])
    get_admin_emails(app.config["ADMINS_PATH"], seeded_admins())

    def current_request_id():
        return getattr(g, "request_id", "")

    def client_ip():
        return request.remote_addr or "unknown"

    def site_origin():
        configured = str(app.config.get("SITE_URL", "")).strip().rstrip("/")
        if configured:
            return configured
        return request.url_root.rstrip("/")

    def absolute_url(value):
        if not value:
            return ""

        parsed = urlsplit(value)
        if parsed.scheme in {"http", "https"}:
            return value

        path = value if value.startswith("/") else f"/{value}"
        return f"{site_origin()}{path}"

    def public_metadata(content):
        site_name = content["site"]["site_name"].strip()
        page_title = f"{content['site']['page_title']} | {site_name}"
        description = content["site"]["meta_description"].strip()
        social_image = absolute_url(
            app.config.get("SOCIAL_IMAGE_URL") or url_for("static", filename=DEFAULT_SOCIAL_IMAGE)
        )
        locale = str(app.config.get("SITE_LOCALE", "sv_SE")).strip() or "sv_SE"
        language = locale.replace("_", "-")
        twitter_handle = str(app.config.get("SITE_TWITTER_HANDLE", "")).strip()
        structured_data = [
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": site_name,
                "url": absolute_url(url_for("index")),
                "description": description,
                "inLanguage": language,
            },
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": site_name,
                "url": site_origin(),
                "logo": absolute_url(url_for("favicon")),
                "description": description,
                "email": content["association"]["contact"]["email"],
            },
        ]

        return {
            "page_title": page_title,
            "description": description,
            "canonical_url": absolute_url(url_for("index")),
            "social_image_url": social_image,
            "social_image_alt": f"{site_name} social share card",
            "locale": locale,
            "twitter_card": "summary_large_image",
            "twitter_handle": twitter_handle,
            "structured_data": structured_data,
        }

    def render_public_error(status_code, title, heading, message):
        try:
            site_name = public_content()["site"]["site_name"]
        except Exception:
            site_name = get_default_site_content()["site"]["site_name"]

        return (
            render_template(
                "error.html",
                status_code=status_code,
                title=title,
                heading=heading,
                message=message,
                site_name=site_name,
            ),
            status_code,
        )

    def build_sitemap_entries(content):
        entries = []
        updated_at = content.get("meta", {}).get("updated_at", "")
        entries.append(
            {
                "loc": absolute_url(url_for("index")),
                "lastmod": updated_at or None,
            }
        )

        documents_root = Path(app.config["DOCUMENTS_FOLDER"])
        for document in sorted(documents_root.rglob("*.pdf")):
            last_modified = datetime.fromtimestamp(document.stat().st_mtime, tz=timezone.utc).date().isoformat()
            entries.append(
                {
                    "loc": absolute_url(
                        url_for("document_file", filename=document.relative_to(documents_root).as_posix())
                    ),
                    "lastmod": last_modified,
                }
            )

        return entries

    def audit_admin_event(action, admin=None, target="", details=None):
        actor = admin or current_admin() or {}
        event = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "request_id": current_request_id(),
            "action": action,
            "actor_email": actor.get("email", ""),
            "actor_name": actor.get("name", ""),
            "ip": client_ip(),
        }
        if target:
            event["target"] = target
        if details:
            event["details"] = details

        append_audit_event(app.config["AUDIT_LOG_PATH"], event)

    def log_auth_rejection(reason, email=""):
        app.logger.warning(
            "request_id=%s event=admin_auth_rejected ip=%s email=%s reason=%s",
            current_request_id(),
            client_ip(),
            email or "-",
            reason,
        )

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

    def rate_limited(bucket_name, limit_key, window_key, key_builder, message):
        def decorator(view):
            @wraps(view)
            def wrapped_view(*args, **kwargs):
                key = key_builder()
                allowed, retry_after = rate_limiter.allow(
                    bucket_name,
                    key,
                    int(app.config.get(limit_key, 0)),
                    int(app.config.get(window_key, 0)),
                )
                if allowed:
                    return view(*args, **kwargs)

                app.logger.warning(
                    "request_id=%s event=rate_limited bucket=%s key=%s retry_after=%s",
                    current_request_id(),
                    bucket_name,
                    key,
                    retry_after,
                )
                response = jsonify({"error": message})
                response.status_code = 429
                response.headers["Retry-After"] = str(retry_after)
                return response

            return wrapped_view

        return decorator

    def csrf_protected(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            expected_token = csrf_token()
            provided_token = (
                request.headers.get(CSRF_HEADER)
                or request.form.get("csrf_token", "")
            ).strip()

            if not provided_token or not compare_digest(provided_token, expected_token):
                abort(403, "Invalid CSRF token")

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
            log_auth_rejection("email_not_verified", email=email)
            abort(401, "Google account email is not verified")

        required_domain = str(app.config.get("GOOGLE_HOSTED_DOMAIN", "")).strip()
        if required_domain and hosted_domain != required_domain:
            log_auth_rejection("invalid_domain", email=email)
            abort(403, "Google account is not part of the allowed domain")

        allowed_admins = set(get_admin_emails(app.config["ADMINS_PATH"], seeded_admins()))
        if email not in allowed_admins:
            log_auth_rejection("email_not_allowlisted", email=email)
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
        if error.code == 404:
            return render_public_error(
                404,
                "Sidan hittades inte",
                "Sidan finns inte",
                "Länken är fel eller sidan har flyttats. Gå tillbaka till startsidan och försök igen.",
            )
        return render_public_error(
            error.code,
            error.name,
            error.name,
            error.description,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception(
            "request_id=%s event=unhandled_exception path=%s",
            current_request_id(),
            request.path,
        )
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error"}), 500
        return render_public_error(
            500,
            "Något gick fel",
            "Webbplatsen kunde inte visas",
            "Ett oväntat fel inträffade. Försök igen om en stund.",
        )

    @app.before_request
    def prepare_request_context():
        g.request_started_at = time.perf_counter()
        incoming_request_id = str(request.headers.get(REQUEST_ID_HEADER, "")).strip()
        g.request_id = incoming_request_id if REQUEST_ID_PATTERN.fullmatch(incoming_request_id) else token_urlsafe(12)
        ensure_csp_nonce()

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(REQUEST_ID_HEADER, current_request_id())
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), geolocation=(), microphone=()",
        )

        if (
            request.path.startswith("/admin")
            or request.path.startswith("/api/")
            or request.path.startswith("/api/admin/")
            or request.path.startswith("/api/auth/")
            or request.path == "/healthz"
        ):
            response.headers.setdefault("Cache-Control", "no-store")
            response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")

        script_sources = ["'self'", f"'nonce-{ensure_csp_nonce()}'", "https://accounts.google.com"]
        csp = "; ".join(
            [
                "default-src 'self'",
                f"script-src {' '.join(script_sources)}",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: https:",
                "font-src 'self'",
                "connect-src 'self' https://accounts.google.com",
                (
                    "frame-src 'self' https://accounts.google.com "
                    "https://www.youtube.com https://www.youtube-nocookie.com"
                ),
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'self'",
            ]
        )
        response.headers.setdefault("Content-Security-Policy", csp)

        static_filename = str((request.view_args or {}).get("filename", ""))
        if request.endpoint == "static":
            if request.args.get("v") or static_filename.startswith("fonts/"):
                response.headers["Cache-Control"] = (
                    f"public, max-age={app.config['STATIC_IMMUTABLE_MAX_AGE']}, immutable"
                )
            else:
                response.headers["Cache-Control"] = f"public, max-age={app.config['STATIC_DEFAULT_MAX_AGE']}"
        elif request.endpoint in {"favicon", "document_file", "robots_txt", "sitemap", "site_manifest"}:
            response.headers["Cache-Control"] = f"public, max-age={app.config['PUBLIC_FILE_MAX_AGE']}"

        if request.endpoint != "static":
            duration_ms = (time.perf_counter() - getattr(g, "request_started_at", time.perf_counter())) * 1000
            admin_email = "-"
            if request.path.startswith("/admin") or request.path.startswith("/api/"):
                admin_email = normalize_email(session.get("admin_email")) or "-"
            app.logger.info(
                "request_id=%s method=%s path=%s status=%s duration_ms=%.2f ip=%s admin=%s",
                current_request_id(),
                request.method,
                request.path,
                response.status_code,
                duration_ms,
                client_ip(),
                admin_email,
            )

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

        return {
            "format_public_timestamp": format_public_timestamp,
            "csp_nonce": ensure_csp_nonce(),
            "asset_url": asset_url,
        }

    @app.route("/")
    def index():
        content = public_content()
        return render_template("index.html", content=content, seo=public_metadata(content))

    @app.route("/favicon.png")
    def favicon():
        return app.send_static_file("favicon.png")

    @app.get("/robots.txt")
    def robots_txt():
        lines = [
            "User-agent: *",
            "Allow: /",
            "Disallow: /admin",
            "Disallow: /api/",
            "Disallow: /healthz",
            f"Sitemap: {absolute_url(url_for('sitemap'))}",
        ]
        return app.response_class("\n".join(lines) + "\n", mimetype="text/plain")

    @app.get("/sitemap.xml")
    def sitemap():
        content = public_content()
        urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for entry in build_sitemap_entries(content):
            url_element = SubElement(urlset, "url")
            SubElement(url_element, "loc").text = entry["loc"]
            if entry.get("lastmod"):
                SubElement(url_element, "lastmod").text = entry["lastmod"]

        xml = tostring(urlset, encoding="utf-8", xml_declaration=True)
        return app.response_class(xml, mimetype="application/xml")

    @app.get("/site.webmanifest")
    def site_manifest():
        content = public_content()
        response = jsonify(
            {
                "name": content["site"]["site_name"],
                "short_name": content["site"]["site_name"],
                "lang": "sv",
                "start_url": url_for("index"),
                "display": "standalone",
                "background_color": content["site"]["theme_color"],
                "theme_color": content["site"]["theme_color"],
                "icons": [
                    {
                        "src": url_for("favicon"),
                        "sizes": "512x512",
                        "type": "image/png",
                    }
                ],
            }
        )
        response.mimetype = "application/manifest+json"
        return response

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
            csrf_token=csrf_token(),
            google_client_id=app.config.get("GOOGLE_CLIENT_ID", ""),
            hosted_domain=app.config.get("GOOGLE_HOSTED_DOMAIN", ""),
        )

    @app.route("/admin")
    @login_required
    def admin():
        return render_template(
            "admin.html",
            admin=current_admin(),
            csrf_token=csrf_token(),
            public_url=url_for("index"),
        )

    @app.post("/admin/logout")
    @login_required
    @csrf_protected
    def admin_logout():
        audit_admin_event("auth.logout")
        session.clear()
        return redirect(url_for("admin_login"))

    @app.post("/api/auth/google")
    @csrf_protected
    @rate_limited(
        "auth.google",
        "AUTH_RATE_LIMIT_MAX_ATTEMPTS",
        "AUTH_RATE_LIMIT_WINDOW_SECONDS",
        key_builder=client_ip,
        message="Too many login attempts. Try again in a few minutes.",
    )
    def admin_google_login():
        identity = validate_admin_identity(json_payload())
        session.clear()
        session.permanent = True
        session["admin_email"] = identity["email"]
        session["admin_name"] = identity["name"]
        session["admin_picture"] = identity["picture"]
        audit_admin_event("auth.login", admin=identity)
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
    @csrf_protected
    @rate_limited(
        "admin.mutations",
        "ADMIN_MUTATION_RATE_LIMIT_MAX_REQUESTS",
        "ADMIN_MUTATION_RATE_LIMIT_WINDOW_SECONDS",
        key_builder=lambda: f"{client_ip()}:{(current_admin() or {}).get('email', '-')}",
        message="Too many admin changes. Wait a moment before trying again.",
    )
    def update_content():
        content = json_payload()
        try:
            validate_site_content(content, get_default_site_content())
        except ContentValidationError as error:
            abort(400, str(error))

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
        audit_admin_event("content.save", admin=admin_user)
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
    @csrf_protected
    @rate_limited(
        "admin.mutations",
        "ADMIN_MUTATION_RATE_LIMIT_MAX_REQUESTS",
        "ADMIN_MUTATION_RATE_LIMIT_WINDOW_SECONDS",
        key_builder=lambda: f"{client_ip()}:{(current_admin() or {}).get('email', '-')}",
        message="Too many admin changes. Wait a moment before trying again.",
    )
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
        audit_admin_event("content.restore", admin=admin_user, target=backup_id)

        return jsonify({"ok": True, "content": restored})

    @app.get("/api/admin/admins")
    @login_required
    def list_admins():
        return jsonify({"emails": get_admin_emails(app.config["ADMINS_PATH"], seeded_admins())})

    @app.post("/api/admin/admins")
    @login_required
    @csrf_protected
    @rate_limited(
        "admin.mutations",
        "ADMIN_MUTATION_RATE_LIMIT_MAX_REQUESTS",
        "ADMIN_MUTATION_RATE_LIMIT_WINDOW_SECONDS",
        key_builder=lambda: f"{client_ip()}:{(current_admin() or {}).get('email', '-')}",
        message="Too many admin changes. Wait a moment before trying again.",
    )
    def create_admin():
        payload = json_payload()
        email = payload.get("email")
        try:
            emails = add_admin_email(app.config["ADMINS_PATH"], email)
        except (ContentValidationError, ValueError) as error:
            abort(400, str(error))

        audit_admin_event("admin.add", target=normalize_email(email))
        return jsonify({"ok": True, "emails": emails})

    @app.delete("/api/admin/admins")
    @login_required
    @csrf_protected
    @rate_limited(
        "admin.mutations",
        "ADMIN_MUTATION_RATE_LIMIT_MAX_REQUESTS",
        "ADMIN_MUTATION_RATE_LIMIT_WINDOW_SECONDS",
        key_builder=lambda: f"{client_ip()}:{(current_admin() or {}).get('email', '-')}",
        message="Too many admin changes. Wait a moment before trying again.",
    )
    def delete_admin():
        payload = json_payload()
        target_email = normalize_email(payload.get("email"))
        try:
            emails = remove_admin_email(app.config["ADMINS_PATH"], payload.get("email"))
        except KeyError:
            abort(404, "Admin account not found")
        except RuntimeError as error:
            abort(400, str(error))

        audit_admin_event("admin.remove", target=target_email)

        if target_email == normalize_email(session.get("admin_email")):
            session.clear()

        return jsonify({"ok": True, "emails": emails})

    @app.post("/api/admin/uploads/documents")
    @login_required
    @csrf_protected
    @rate_limited(
        "admin.mutations",
        "ADMIN_MUTATION_RATE_LIMIT_MAX_REQUESTS",
        "ADMIN_MUTATION_RATE_LIMIT_WINDOW_SECONDS",
        key_builder=lambda: f"{client_ip()}:{(current_admin() or {}).get('email', '-')}",
        message="Too many admin changes. Wait a moment before trying again.",
    )
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
        audit_admin_event("document.upload", target=f"{year}/{filename}")

        return jsonify({"ok": True, "url": f"/documents/{year}/{filename}"})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("FLASK_RUN_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=parse_bool(os.environ.get("FLASK_DEBUG"), default=False),
    )
