import json
import re
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from app import create_app


class WebsiteAdminTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temporary_directory.name)
        self.app_config = {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "GOOGLE_CLIENT_ID": "test-client-id",
            "CONTENT_PATH": self.base_path / "site-content.json",
            "ADMINS_PATH": self.base_path / "admins.json",
            "DOCUMENTS_FOLDER": self.base_path / "documents",
            "BACKUPS_DIR": self.base_path / "backups",
            "AUDIT_LOG_PATH": self.base_path / "admin-audit.jsonl",
            "INITIAL_ADMIN_EMAILS": "admin@example.com",
            "SITE_URL": "https://example.com",
            "LOG_LEVEL": "ERROR",
            "VERIFY_GOOGLE_TOKEN_FUNC": lambda credential: {
                "email": "admin@example.com",
                "email_verified": True,
                "name": "Test Admin",
                "picture": "https://example.com/avatar.png",
                "hd": "",
            },
        }
        self.app = create_app(self.app_config)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def csrf_token(self, path="/admin/login", client=None):
        client = client or self.client
        client.get(path)
        with client.session_transaction() as session:
            return session["_csrf_token"]

    def csrf_headers(self, path="/admin/login", client=None):
        return {"X-CSRF-Token": self.csrf_token(path=path, client=client)}

    def login(self, client=None):
        client = client or self.client
        response = client.post(
            "/api/auth/google",
            json={"credential": "test-token"},
            headers=self.csrf_headers("/admin/login", client=client),
        )
        self.assertEqual(response.status_code, 200)

    def read_audit_events(self, app=None):
        app = app or self.app
        audit_path = Path(app.config["AUDIT_LOG_PATH"])
        if not audit_path.exists():
            return []

        return [
            json.loads(line)
            for line in audit_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_public_homepage_renders_default_content(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Tullinge gymnasium datorklubb", response.get_data(as_text=True))
        self.assertIn("Välkommen till Tullinge gymnasium datorklubb", response.get_data(as_text=True))

    def test_public_homepage_includes_seo_metadata(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('<html lang="sv-SE">', html)
        self.assertIn('<link rel="canonical" href="https://example.com/" />', html)
        self.assertIn('<link rel="alternate" hreflang="sv-SE" href="https://example.com/" />', html)
        self.assertIn('property="og:title"', html)
        self.assertIn('property="og:image" content="https://example.com/static/social-preview.png"', html)
        self.assertIn('property="og:image:type" content="image/png"', html)
        self.assertIn('name="twitter:card" content="summary_large_image"', html)
        self.assertIn('type="application/ld+json"', html)
        self.assertIn('"@context": "https://schema.org"', html)
        self.assertIn('"@type": "CollectionPage"', html)
        self.assertIn('<link rel="manifest" href="/manifest.json" />', html)
        self.assertIn('<link rel="alternate" type="application/json" href="/data.json" />', html)
        self.assertIn('name="description" content="Elevförening på Tullinge gymnasium med LAN, programmering, Minecraft och elevdrivna projekt."', html)
        self.assertIn('<p class="site-title">', html)
        self.assertIn('href="/privacy-policy.html"', html)
        self.assertIn('href="/terms-of-service.html"', html)

    def test_public_homepage_does_not_create_session_cookie(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Set-Cookie", response.headers)
        self.assertNotIn("Cookie", response.headers.get("Vary", ""))

    def test_public_metadata_routes_exist(self):
        robots_response = self.client.get("/robots.txt")
        sitemap_response = self.client.get("/sitemap.xml")
        manifest_response = self.client.get("/site.webmanifest")
        manifest_json_response = self.client.get("/manifest.json")
        data_response = self.client.get("/data.json")

        self.assertEqual(robots_response.status_code, 200)
        self.assertIn("text/plain", robots_response.content_type)
        self.assertIn("Sitemap: https://example.com/sitemap.xml", robots_response.get_data(as_text=True))
        self.assertIn("Disallow: /admin", robots_response.get_data(as_text=True))

        self.assertEqual(sitemap_response.status_code, 200)
        self.assertIn("application/xml", sitemap_response.content_type)
        self.assertIn("https://example.com/", sitemap_response.get_data(as_text=True))

        self.assertEqual(manifest_response.status_code, 200)
        self.assertEqual(manifest_response.content_type, "application/manifest+json")
        self.assertEqual(manifest_response.get_json()["start_url"], "/")
        self.assertEqual(
            manifest_response.get_json()["description"],
            "Elevförening på Tullinge gymnasium med LAN, programmering, Minecraft och elevdrivna projekt.",
        )
        self.assertEqual(manifest_json_response.status_code, 200)
        self.assertEqual(manifest_json_response.content_type, "application/manifest+json")
        self.assertEqual(manifest_json_response.get_json(), manifest_response.get_json())
        self.assertEqual(data_response.status_code, 200)
        self.assertEqual(data_response.get_json()["@context"], "https://schema.org")
        self.assertIn("@graph", data_response.get_json())

    def test_legal_pages_exist(self):
        privacy_response = self.client.get("/privacy-policy.html")
        terms_response = self.client.get("/terms-of-service.html")

        self.assertEqual(privacy_response.status_code, 200)
        self.assertEqual(terms_response.status_code, 200)
        self.assertIn("Integritetspolicy", privacy_response.get_data(as_text=True))
        self.assertIn("Användarvillkor", terms_response.get_data(as_text=True))

    def test_admin_login_and_content_save_flow(self):
        self.login()

        before = self.client.get("/api/admin/content")
        self.assertEqual(before.status_code, 200)
        payload = before.get_json()
        payload["hero"]["title"] = "Ny rubrik för webbplatsen"
        payload["association"]["contact"]["email"] = "kontakt@tgdk.se"

        saved = self.client.put(
            "/api/admin/content",
            json=payload,
            headers=self.csrf_headers("/admin"),
        )
        self.assertEqual(saved.status_code, 200)
        saved_payload = saved.get_json()["content"]
        self.assertEqual(saved_payload["hero"]["title"], "Ny rubrik för webbplatsen")
        self.assertEqual(saved_payload["association"]["contact"]["email"], "kontakt@tgdk.se")
        self.assertEqual(saved_payload["meta"]["updated_by_name"], "Test Admin")

        public_response = self.client.get("/")
        public_text = public_response.get_data(as_text=True)
        self.assertIn("Ny rubrik för webbplatsen", public_text)
        self.assertIn("kontakt@tgdk.se", public_text)

    def test_content_history_and_restore_flow(self):
        self.login()

        original = self.client.get("/api/admin/content").get_json()
        updated = self.client.get("/api/admin/content").get_json()
        updated["hero"]["title"] = "Första ändringen"

        saved = self.client.put(
            "/api/admin/content",
            json=updated,
            headers=self.csrf_headers("/admin"),
        )
        self.assertEqual(saved.status_code, 200)

        history = self.client.get("/api/admin/history")
        self.assertEqual(history.status_code, 200)
        items = history.get_json()["items"]
        self.assertGreaterEqual(len(items), 1)
        self.assertEqual(items[0]["reason"], "save")
        self.assertEqual(items[0]["actor_name"], "Test Admin")

        restored = self.client.post(
            "/api/admin/history/restore",
            json={"backup_id": items[0]["id"]},
            headers=self.csrf_headers("/admin"),
        )
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.get_json()["content"]["hero"]["title"], original["hero"]["title"])

        public_response = self.client.get("/")
        self.assertIn(original["hero"]["title"], public_response.get_data(as_text=True))

    def test_admin_actions_write_audit_log(self):
        self.login()

        payload = self.client.get("/api/admin/content").get_json()
        payload["hero"]["title"] = "Audit log title"
        response = self.client.put(
            "/api/admin/content",
            json=payload,
            headers=self.csrf_headers("/admin"),
        )
        self.assertEqual(response.status_code, 200)

        actions = [event["action"] for event in self.read_audit_events()]
        self.assertIn("auth.login", actions)
        self.assertIn("content.save", actions)

    def test_admin_list_management(self):
        self.login()

        created = self.client.post(
            "/api/admin/admins",
            json={"email": "new-admin@example.com"},
            headers=self.csrf_headers("/admin"),
        )
        self.assertEqual(created.status_code, 200)
        self.assertIn("new-admin@example.com", created.get_json()["emails"])

        deleted = self.client.delete(
            "/api/admin/admins",
            json={"email": "new-admin@example.com"},
            headers=self.csrf_headers("/admin"),
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertNotIn("new-admin@example.com", deleted.get_json()["emails"])

        blocked = self.client.delete(
            "/api/admin/admins",
            json={"email": "admin@example.com"},
            headers=self.csrf_headers("/admin"),
        )
        self.assertEqual(blocked.status_code, 400)

    def test_document_upload_requires_admin_and_saves_pdf(self):
        unauthorized = self.client.post(
            "/api/admin/uploads/documents",
            data={"year": "2026", "file": (BytesIO(b"%PDF-1.4"), "minutes.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(unauthorized.status_code, 401)

        self.login()

        uploaded = self.client.post(
            "/api/admin/uploads/documents",
            data={"year": "2026", "file": (BytesIO(b"%PDF-1.4"), "minutes.pdf")},
            headers=self.csrf_headers("/admin"),
            content_type="multipart/form-data",
        )
        self.assertEqual(uploaded.status_code, 200)
        self.assertEqual(uploaded.get_json()["url"], "/documents/2026/minutes.pdf")
        self.assertTrue((self.base_path / "documents" / "2026" / "minutes.pdf").exists())

        sitemap_response = self.client.get("/sitemap.xml")
        self.assertIn("/documents/2026/minutes.pdf", sitemap_response.get_data(as_text=True))

    def test_document_upload_rejects_invalid_year_and_fake_pdf(self):
        self.login()

        invalid_year = self.client.post(
            "/api/admin/uploads/documents",
            data={"year": "20AB", "file": (BytesIO(b"%PDF-1.4"), "minutes.pdf")},
            headers=self.csrf_headers("/admin"),
            content_type="multipart/form-data",
        )
        self.assertEqual(invalid_year.status_code, 400)
        self.assertIn("Year must use four digits", invalid_year.get_json()["error"])

        fake_pdf = self.client.post(
            "/api/admin/uploads/documents",
            data={"year": "2026", "file": (BytesIO(b"not-a-pdf"), "minutes.pdf")},
            headers=self.csrf_headers("/admin"),
            content_type="multipart/form-data",
        )
        self.assertEqual(fake_pdf.status_code, 400)
        self.assertIn("valid PDF", fake_pdf.get_json()["error"])

    def test_admin_mutations_require_csrf_token(self):
        self.login()

        response = self.client.post("/api/admin/admins", json={"email": "new-admin@example.com"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("CSRF", response.get_json()["error"])

    def test_content_save_rejects_invalid_urls(self):
        self.login()

        payload = self.client.get("/api/admin/content").get_json()
        payload["intro"]["link"]["url"] = "javascript:alert(1)"

        response = self.client.put(
            "/api/admin/content",
            json=payload,
            headers=self.csrf_headers("/admin"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("intro.link.url", response.get_json()["error"])

    def test_content_save_rejects_unexpected_fields(self):
        self.login()

        payload = self.client.get("/api/admin/content").get_json()
        payload["hero"]["unexpected"] = "value"

        response = self.client.put(
            "/api/admin/content",
            json=payload,
            headers=self.csrf_headers("/admin"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("unexpected fields", response.get_json()["error"])

    def test_healthcheck(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ok"], True)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["X-Robots-Tag"], "noindex, nofollow")

    def test_public_templates_use_versioned_static_assets(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertRegex(html, r'/static/styles\.css\?v=\d+')
        self.assertRegex(html, r'/static/script\.js\?v=\d+')
        self.assertRegex(html, r'/static/fonts/roboto-v27-latin-regular\.woff2\?v=\d+')

    def test_versioned_static_assets_are_immutable(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)
        styles_match = re.search(r'(/static/styles\.css\?v=\d+)', html)
        script_match = re.search(r'(/static/script\.js\?v=\d+)', html)

        self.assertIsNotNone(styles_match)
        self.assertIsNotNone(script_match)

        styles_response = self.client.get(styles_match.group(1))
        script_response = self.client.get(script_match.group(1))

        self.assertEqual(styles_response.headers["Cache-Control"], "public, max-age=31536000, immutable")
        self.assertEqual(script_response.headers["Cache-Control"], "public, max-age=31536000, immutable")
        styles_response.close()
        script_response.close()

    def test_fonts_and_public_files_get_public_cache_headers(self):
        font_response = self.client.get("/static/fonts/roboto-v27-latin-regular.woff2")
        favicon_response = self.client.get("/favicon.png")
        manifest_response = self.client.get("/manifest.json")
        data_response = self.client.get("/data.json")

        self.assertEqual(font_response.status_code, 200)
        self.assertEqual(favicon_response.status_code, 200)
        self.assertEqual(font_response.headers["Cache-Control"], "public, max-age=31536000, immutable")
        self.assertEqual(favicon_response.headers["Cache-Control"], "public, max-age=3600")
        self.assertEqual(manifest_response.headers["Cache-Control"], "public, max-age=3600")
        self.assertEqual(data_response.headers["Cache-Control"], "public, max-age=3600")
        font_response.close()
        favicon_response.close()
        manifest_response.close()
        data_response.close()

    def test_public_and_admin_responses_include_request_ids(self):
        homepage_response = self.client.get("/", headers={"X-Request-ID": "public-request-123"})
        admin_login_response = self.client.get("/admin/login")

        self.assertEqual(homepage_response.headers["X-Request-ID"], "public-request-123")
        self.assertTrue(admin_login_response.headers["X-Request-ID"])
        self.assertEqual(admin_login_response.headers["X-Robots-Tag"], "noindex, nofollow")

    def test_public_pages_include_security_headers(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
        self.assertTrue(response.headers["X-Request-ID"])

    def test_https_responses_include_hsts(self):
        response = self.client.get("/", base_url="https://example.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Strict-Transport-Security"], "max-age=31536000; includeSubDomains")

    def test_public_404_page_is_branded(self):
        response = self.client.get("/missing-page")

        self.assertEqual(response.status_code, 404)
        self.assertIn("Sidan finns inte", response.get_data(as_text=True))
        self.assertIn("Till startsidan", response.get_data(as_text=True))

    def test_favicon_ico_redirects_to_png(self):
        response = self.client.get("/favicon.ico")

        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.headers["Location"], "/favicon.png")

    def test_public_500_page_is_branded(self):
        app = create_app(
            {
                **self.app_config,
                "TESTING": False,
                "PROPAGATE_EXCEPTIONS": False,
            }
        )

        @app.get("/boom")
        def boom():
            raise RuntimeError("boom")

        client = app.test_client()
        response = client.get("/boom")

        self.assertEqual(response.status_code, 500)
        self.assertIn("Webbplatsen kunde inte visas", response.get_data(as_text=True))

    def test_auth_rate_limit_returns_429(self):
        app = create_app(
            {
                **self.app_config,
                "AUTH_RATE_LIMIT_MAX_ATTEMPTS": 1,
                "AUTH_RATE_LIMIT_WINDOW_SECONDS": 3600,
            }
        )
        client = app.test_client()
        first_headers = self.csrf_headers("/admin/login", client=client)

        first = client.post(
            "/api/auth/google",
            json={"credential": "test-token"},
            headers=first_headers,
        )
        second = client.post(
            "/api/auth/google",
            json={"credential": "test-token"},
            headers=self.csrf_headers("/admin", client=client),
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("Retry-After", second.headers)

    def test_production_environment_requires_secret_key(self):
        with self.assertRaises(RuntimeError):
            create_app(
                {
                    "APP_ENV": "production",
                    "SECRET_KEY": "",
                    "CONTENT_PATH": self.base_path / "prod-site-content.json",
                    "ADMINS_PATH": self.base_path / "prod-admins.json",
                    "DOCUMENTS_FOLDER": self.base_path / "prod-documents",
                    "BACKUPS_DIR": self.base_path / "prod-backups",
                }
            )


if __name__ == "__main__":
    unittest.main()
