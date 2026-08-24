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
Dockerfile          container for cloud deploy (Render/Koyeb/Cloud Run)
```

## Deploy to Render (Web Service — no blueprint)

1. Render dashboard → **New +** → **Web Service** → connect this GitHub repo
2. **Runtime:** Docker · **Instance:** Free
3. Create/link a **Postgres** instance (Render → New + → Postgres, free plan) and copy its *Internal Database URL*
4. Add these environment variables (Dashboard → Web Service → Environment):

| Key | Value | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://user:pass@host/db` | From the Postgres *Internal Database URL*; keep the `postgresql+psycopg://` scheme |
| `JWT_SECRET` | long random string (32+) | e.g. `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `VAULT_MASTER_KEY` | base64 of 32 bytes | `python -c "from app.crypto import generate_master_key_b64; print(generate_master_key_b64())"` |
| `INITIAL_ADMIN_USERNAME` | `admin` | Seed account, created only if no admin exists |
| `INITIAL_ADMIN_PASSWORD` | your chosen password | Read once at seed time; changing later does NOT update the password |
| `SYNC_ADMIN_PASSWORD` | `true` only while recovering access | Resets seeded admin's password on every boot; remove after use |
| `CORS_ORIGINS` | `*` | Or comma-separated origins |
| `ENVIRONMENT` | `production` | |
| `OPENCODE_API_KEY` | *(optional)* AI provider key | Enables AI-assisted category suggestions during import; without it, rule-based categorization runs silently |
| `OPENCODE_API_BASE` | *(optional)* OpenAI-compatible base URL | Default `https://api.openai.com/v1` |
| `OPENCODE_MODEL` | *(optional)* chat model name | Default `gpt-4o-mini` |

5. Deploy. The service serves both the API and the admin website from one URL.
6. Check **Logs** at startup — you should see `Vault master key loaded OK`. If you see `VAULT MASTER KEY MISCONFIGURED`, the key is not valid base64-encoded 32 bytes; regenerate with the command above. Never change `VAULT_MASTER_KEY` after entries exist — old ciphertexts become undecryptable.

> Note: there is intentionally **no `render.yaml` blueprint** in this repo — deploy manually as a Web Service so environment values are controlled in the dashboard.

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

## Deploy (Free: Render web + Neon Postgres)

**Total cost: $0/month.** Render free web service spins down after 15 min idle (wakes ~30s); Neon free Postgres suspends after 5 min idle (wakes ~2s).

1. **Neon** → sign up (GitHub) → **Create project** → copy the *pooled* connection string  
   Format: `postgresql://user:pass@ep-xxx.neon.tech/vault?sslmode=require`
2. **Render** → **New → Blueprint** → select this repo → it reads `render.yaml` (free web service only)  
   When prompted for `DATABASE_URL`, paste the Neon string → **Apply**
3. Render builds the Docker image and deploys to `https://vault-xxxx.onrender.com`
4. Open the URL → login `admin` / `INITIAL_ADMIN_PASSWORD` (shown in Render → Environment tab, auto-generated) → **change immediately**
5. Admin console → **Users** → create employee accounts → employees log in on mobile with your Render URL

**Local Docker (any host):**
```bash
docker build -t vault .
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql+psycopg://user:pass@host:5432/vault" \
  -e JWT_SECRET="..." \
  -e VAULT_MASTER_KEY="..." \
  -e INITIAL_ADMIN_PASSWORD="..." \
  vault
```

## Security notes

- The vault master key is the crown jewel: it is **never** stored in the database. Losing it means the vault cannot be decrypted.
- Employees can view passwords but never modify them — enforced by the API.
- For production, restrict `CORS_ORIGINS` to your admin domain and force HTTPS (Render/Railway do this by default).
- Legacy `.xls` files are rejected; use `.xlsx` or `.csv`.