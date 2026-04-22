# TGDK Website

Website with a public page and a separate admin interface for editing content without touching code.

## What Changed

- The public site now renders from structured content instead of hardcoded HTML.
- The admin interface lives at `/admin`.
- Admin access is restricted to approved Google accounts.
- Site content is stored on disk in `data/site-content.json`.
- Admin accounts are stored on disk in `data/admins.json`.
- Every save creates an automatic restore point in `data/backups/`.

## Local Setup

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Required environment variables:

- `SECRET_KEY` - Flask session secret
- `INITIAL_ADMIN_EMAILS` - comma-separated Google emails allowed to access the admin UI
- `GOOGLE_CLIENT_ID` - Google Identity Services client ID for the admin login button

Optional environment variables:

- `GOOGLE_HOSTED_DOMAIN` - restrict admin login to one Google Workspace domain
- `SESSION_COOKIE_SECURE=1` - enable secure cookies in production
- `BACKUP_KEEP_COUNT` - how many previous content versions to keep, default `25`
- `APP_ENV=production` - turn on production safety checks
- `TRUSTED_HOSTS` - comma-separated allowed hostnames, recommended in production
- `TRUST_PROXY_HEADERS=1` - trust `X-Forwarded-*` headers only when running behind your own reverse proxy

## Run Locally

```bash
SECRET_KEY=dev-secret \
INITIAL_ADMIN_EMAILS=admin@example.com \
GOOGLE_CLIENT_ID=your-google-client-id \
.venv/bin/python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

Admin login is available at:

```text
http://127.0.0.1:5000/admin
```

## Production Notes

For production, run behind a reverse proxy and use a real secret key:

```bash
APP_ENV=production \
SECRET_KEY=replace-this-with-a-long-random-secret \
INITIAL_ADMIN_EMAILS=admin@example.com \
GOOGLE_CLIENT_ID=your-google-client-id \
TRUSTED_HOSTS=example.com,www.example.com \
SESSION_COOKIE_SECURE=1 \
.venv/bin/gunicorn --bind 0.0.0.0:5000 app:app
```

If your hosting platform terminates TLS before the Flask app, enable `TRUST_PROXY_HEADERS=1` only when those proxy headers come from infrastructure you control.

## Google Setup

Create a Google Identity Services web client and add your local/dev/prod origins as authorized JavaScript origins.

Typical examples:

- `http://127.0.0.1:5000`
- `http://localhost:5000`
- your production admin origin

The backend verifies the Google ID token and then checks that the email is in the admin allowlist.

## Recovery and Low-Maintenance Operation

- Every content save automatically creates a restore point.
- Admins can restore earlier versions directly from the admin UI.
- Admins can add or remove other approved Google accounts from the admin UI.
- Uploaded PDFs stay on disk in the website project and keep working through `/documents/...`.
- A simple health endpoint is available at `/healthz` for hosting checks.
- Admin and auth responses are sent with `Cache-Control: no-store` to avoid stale sensitive pages.
- The app adds baseline security headers such as `Referrer-Policy`, `X-Content-Type-Options`, and `X-Frame-Options`.

## Content and Uploads

- `data/site-content.json` is created automatically on first start.
- `data/admins.json` is created automatically on first start.
- `data/backups/` is created automatically and stores restore points.
- Uploaded PDFs are stored in `static/documents/<year>/`.
- Existing legacy document URLs continue to work through the Flask app.

## Main Files

- `app.py` - Flask app, routes, auth flow, content API, uploads
- `default_content.py` - seeded content used on first boot
- `content_store.py` - JSON persistence and admin allowlist storage
- `templates/` - public page and admin templates
- `static/styles.css` - public site styling
- `static/script.js` - public site navigation behavior
- `static/admin.css` - admin interface styling
- `static/admin.js` - admin editor behavior
- `static/admin-login.js` - Google login handling

## Testing

Run the automated checks with:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## License

Unless otherwise noted, the current source code for this rewritten website is licensed under the MIT License. See [LICENSE](LICENSE).

That license applies to the software in this repository, including the Flask app, templates, and project-authored frontend code.

It does not automatically apply to club documents, uploaded PDFs, fonts, logos, images, or other third-party or non-code assets that may be included in or used by the project. Those materials remain subject to their own copyright or license terms.

Historical repository contents and prior revisions also remain subject to their respective copyrights.
