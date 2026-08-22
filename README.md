# Vault — Password Manager

A two-role password vault: **admins** manage credentials from a web console; **employees** view them read-only from a mobile app.

```
┌─────────────────────┐     ┌──────────────────────────────┐     ┌──────────────────┐
│ Admin Website       │     │ FastAPI Backend (Cloud)      │     │ Flutter App      │
│ Login, CRUD,        │────▶│ JWT auth (admin/employee)    │◀────│ Employee login,  │
│ import/export CSV,  │     │ AES-256-GCM encrypted vault  │     │ read-only,       │
│ user management     │     │ SQLite/PostgreSQL + audit    │     │ search/reveal    │
└─────────────────────┘     └──────────────────────────────┘     └──────────────────┘
```

## Features

- **Roles enforced server-side** — employee tokens are rejected for all write endpoints (403), not just hidden in the UI
- **Encryption at rest** — every username/password/note encrypted with AES-256-GCM, fresh nonce per field; master key lives only in the environment
- **Import** — CSV from Chrome, Edge, Firefox, Bitwarden, 1Password (auto-detected) + `.xlsx`; preview before commit; duplicate skip; up to 50,000 rows
- **Export** — Chrome-compatible CSV or Excel, decrypted on the fly
- **Audit log** — login, entry/user changes, imports, exports (who, what, when, IP)
- **Searchable UI** — instant search, category filters, password strength, bento dashboard
- **2026 design** — dark-first, Aurora violet→cyan gradient, Fraunces + Inter, glassmorphic overlays, micro-interactions

## Project layout

```
backend/            FastAPI app + admin SPA (served by the backend)
  app/              config, models, crypto, security, routers
  static/           admin website (index.html, css, js)
  tests/            47 pytest tests
mobile/             Flutter app (employees, read-only)
Dockerfile          container for cloud deploy
render.yaml         Render.com blueprint (web + Postgres)
```

## Run locally

### Backend + admin website

```bash
cd backend
py -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
copy .env.example .env            # set JWT_SECRET, admin password
uvicorn app.main:app --port 8000
```

- Admin website: http://localhost:8000
- API docs: http://localhost:8000/api/docs
- Default admin: `admin` / value of `INITIAL_ADMIN_PASSWORD` (change it!)

### Mobile app

```bash
cd mobile
flutter pub get
flutter run                      # needs Android SDK / Xcode
```

On the login screen, enter the server address (e.g. `http://192.168.1.10:8000` on the LAN, or your cloud URL). Employees get accounts from the admin console → Users.

## Tests

```bash
cd backend && .venv\Scripts\python -m pytest tests -q     # 47 tests
cd mobile && flutter analyze && flutter test
```

## Deploy (Render)

1. Push this repo to GitHub
2. New Blueprint → import repo → uses `render.yaml` (web service + Postgres)
3. `VAULT_MASTER_KEY` and `JWT_SECRET` are generated automatically; copy them somewhere safe
4. First login: `admin` / `INITIAL_ADMIN_PASSWORD` (visible in Render env vars once)

Or any Docker host: `docker build -t vault . && docker run -p 8000:8000 -e DATABASE_URL=... -e JWT_SECRET=... -e VAULT_MASTER_KEY=... vault`

## Security notes

- The vault master key is the crown jewel: it is **never** stored in the database. Losing it means the vault cannot be decrypted.
- Employees can view passwords but never modify them — enforced by the API.
- For production, restrict `CORS_ORIGINS` to your admin domain and force HTTPS (Render/Railway do this by default).
- Legacy `.xls` files are rejected; use `.xlsx` or `.csv`.