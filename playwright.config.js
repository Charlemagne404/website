const fs = require("fs");
const path = require("path");
const { defineConfig } = require("@playwright/test");

const e2eRoot = path.join(__dirname, ".tmp", "e2e");
const pythonCommand = fs.existsSync(path.join(__dirname, ".venv", "bin", "python"))
  ? path.join(__dirname, ".venv", "bin", "python")
  : "python3";

module.exports = defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  expect: {
    timeout: 10_000
  },
  fullyParallel: true,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure"
  },
  webServer: {
    command: `"${pythonCommand}" app.py`,
    url: "http://127.0.0.1:4173",
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
    env: {
      ...process.env,
      PORT: "4173",
      SECRET_KEY: "playwright-secret",
      APP_ENV: "development",
      INITIAL_ADMIN_EMAILS: "admin@example.com",
      GOOGLE_CLIENT_ID: "playwright-google-client-id",
      SITE_URL: "http://127.0.0.1:4173",
      CONTENT_PATH: path.join(e2eRoot, "site-content.json"),
      ADMINS_PATH: path.join(e2eRoot, "admins.json"),
      BACKUPS_DIR: path.join(e2eRoot, "backups"),
      DOCUMENTS_FOLDER: path.join(e2eRoot, "documents"),
      AUDIT_LOG_PATH: path.join(e2eRoot, "admin-audit.jsonl")
    }
  }
});
