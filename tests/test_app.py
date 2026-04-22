import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from app import create_app


class WebsiteAdminTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temporary_directory.name)

        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "GOOGLE_CLIENT_ID": "test-client-id",
                "CONTENT_PATH": self.base_path / "site-content.json",
                "ADMINS_PATH": self.base_path / "admins.json",
                "DOCUMENTS_FOLDER": self.base_path / "documents",
                "BACKUPS_DIR": self.base_path / "backups",
                "INITIAL_ADMIN_EMAILS": "admin@example.com",
                "VERIFY_GOOGLE_TOKEN_FUNC": lambda credential: {
                    "email": "admin@example.com",
                    "email_verified": True,
                    "name": "Test Admin",
                    "picture": "https://example.com/avatar.png",
                    "hd": "",
                },
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def login(self):
        response = self.client.post("/api/auth/google", json={"credential": "test-token"})
        self.assertEqual(response.status_code, 200)

    def test_public_homepage_renders_default_content(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Tullinge gymnasium datorklubb", response.get_data(as_text=True))
        self.assertIn("Välkommen till Tullinge gymnasium datorklubb", response.get_data(as_text=True))

    def test_admin_login_and_content_save_flow(self):
        self.login()

        before = self.client.get("/api/admin/content")
        self.assertEqual(before.status_code, 200)
        payload = before.get_json()
        payload["hero"]["title"] = "Ny rubrik för webbplatsen"
        payload["association"]["contact"]["email"] = "kontakt@tgdk.se"

        saved = self.client.put("/api/admin/content", json=payload)
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

        saved = self.client.put("/api/admin/content", json=updated)
        self.assertEqual(saved.status_code, 200)

        history = self.client.get("/api/admin/history")
        self.assertEqual(history.status_code, 200)
        items = history.get_json()["items"]
        self.assertGreaterEqual(len(items), 1)
        self.assertEqual(items[0]["reason"], "save")
        self.assertEqual(items[0]["actor_name"], "Test Admin")

        restored = self.client.post("/api/admin/history/restore", json={"backup_id": items[0]["id"]})
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.get_json()["content"]["hero"]["title"], original["hero"]["title"])

        public_response = self.client.get("/")
        self.assertIn(original["hero"]["title"], public_response.get_data(as_text=True))

    def test_admin_list_management(self):
        self.login()

        created = self.client.post("/api/admin/admins", json={"email": "new-admin@example.com"})
        self.assertEqual(created.status_code, 200)
        self.assertIn("new-admin@example.com", created.get_json()["emails"])

        deleted = self.client.delete("/api/admin/admins", json={"email": "new-admin@example.com"})
        self.assertEqual(deleted.status_code, 200)
        self.assertNotIn("new-admin@example.com", deleted.get_json()["emails"])

        blocked = self.client.delete("/api/admin/admins", json={"email": "admin@example.com"})
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
            content_type="multipart/form-data",
        )
        self.assertEqual(uploaded.status_code, 200)
        self.assertEqual(uploaded.get_json()["url"], "/documents/2026/minutes.pdf")
        self.assertTrue((self.base_path / "documents" / "2026" / "minutes.pdf").exists())

    def test_document_upload_rejects_invalid_year_and_fake_pdf(self):
        self.login()

        invalid_year = self.client.post(
            "/api/admin/uploads/documents",
            data={"year": "20AB", "file": (BytesIO(b"%PDF-1.4"), "minutes.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(invalid_year.status_code, 400)
        self.assertIn("Year must use four digits", invalid_year.get_json()["error"])

        fake_pdf = self.client.post(
            "/api/admin/uploads/documents",
            data={"year": "2026", "file": (BytesIO(b"not-a-pdf"), "minutes.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(fake_pdf.status_code, 400)
        self.assertIn("valid PDF", fake_pdf.get_json()["error"])

    def test_healthcheck(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ok"], True)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_public_pages_include_security_headers(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")

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
