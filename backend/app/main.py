from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import security
from .config import get_settings
from .database import Base, SessionLocal, engine
from .models import AuditLog, User
from .routers import audit, auth, categories, districts, entries, import_export, users
from sqlalchemy import inspect, text

settings = get_settings()
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _ensure_migrations():
    """Lightweight SQLite/Postgres migration for added columns (for Render free deploy without alembic)."""
    try:
        insp = inspect(engine)
        # users
        if "users" in insp.get_table_names():
            cols = {c["name"] for c in insp.get_columns("users")}
            with engine.begin() as conn:
                if "district_id" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN district_id INTEGER"))
                if "block_id" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN block_id INTEGER"))
        if "password_entries" in insp.get_table_names():
            cols = {c["name"] for c in insp.get_columns("password_entries")}
            with engine.begin() as conn:
                if "district_id" not in cols:
                    conn.execute(text("ALTER TABLE password_entries ADD COLUMN district_id INTEGER"))
                if "block_id" not in cols:
                    conn.execute(text("ALTER TABLE password_entries ADD COLUMN block_id INTEGER"))
                if "is_duplicate" not in cols:
                    # Postgres needs FALSE, SQLite accepts 0; use FALSE for compat, SQLite will coerce
                    try:
                        conn.execute(text("ALTER TABLE password_entries ADD COLUMN is_duplicate BOOLEAN NOT NULL DEFAULT FALSE"))
                    except Exception:
                        # fallback for SQLite older
                        conn.execute(text("ALTER TABLE password_entries ADD COLUMN is_duplicate BOOLEAN NOT NULL DEFAULT 0"))
                for col, typ in [
                    ("host", "VARCHAR(255)"),
                    ("exact_host", "VARCHAR(255)"),
                    ("registrable_domain", "VARCHAR(255)"),
                    ("host_group_key", "VARCHAR(255)"),
                    ("smart_category_id", "INTEGER"),
                    ("smart_subcategory_id", "INTEGER"),
                ]:
                    if col not in cols:
                        conn.execute(text(f"ALTER TABLE password_entries ADD COLUMN {col} {typ}"))
        # ensure new tables for districts/blocks etc. already via create_all, but ensure is_duplicate default backfill
        try:
            with engine.begin() as conn:
                conn.execute(text("UPDATE password_entries SET is_duplicate = FALSE WHERE is_duplicate IS NULL"))
                conn.execute(text("UPDATE password_entries SET host = '' WHERE host IS NULL"))
                conn.execute(text("UPDATE password_entries SET host_group_key = COALESCE(registrable_domain, host, '') WHERE host_group_key IS NULL OR host_group_key = ''"))
        except Exception:
            pass
    except Exception:
        pass  # best effort; tests use fresh DB

    # seed system categories
    try:
        from .models import Category
        with SessionLocal() as db:
            if db.query(Category).count() == 0:
                seed = [
                    ("Education", None), ("Finance", None), ("Work", None), ("Government", None),
                    ("Health", None), ("Shopping", None), ("Social", None), ("Other", None),
                ]
                for name, parent in seed:
                    db.add(Category(name=name, slug=name.lower(), parent_id=None, is_system=True))
                db.commit()
                # add LokOS as subcategory of Education for demo
                edu = db.query(Category).filter(Category.name == "Education").first()
                if edu:
                    db.add(Category(name="LokOS", slug="lokos", parent_id=edu.id, is_system=True))
                    db.add(Category(name="LokOS-School", slug="lokos-school", parent_id=edu.id, is_system=True))
                    db.commit()
    except Exception:
        pass


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_migrations()
    seed_admin()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(districts.router)
    app.include_router(categories.router)
    app.include_router(entries.router)
    app.include_router(import_export.router)
    app.include_router(audit.router)

    @app.exception_handler(ValueError)
    async def value_error_handler(_: Request, exc: ValueError):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

        @app.get("/", include_in_schema=False)
        def index():
            return FileResponse(STATIC_DIR / "index.html")

        @app.get("/{path:path}", include_in_schema=False)
        def spa_fallback(path: str):
            target = STATIC_DIR / path
            if target.is_file():
                return FileResponse(target)
            return FileResponse(STATIC_DIR / "index.html")

    return app


def seed_admin() -> None:
    with SessionLocal() as db:
        admin = db.query(User).filter(User.role == "admin").first()
        if admin is None:
            admin = User(
                username=settings.initial_admin_username,
                password_hash=security.hash_password(settings.initial_admin_password),
                role="admin",
            )
            db.add(admin)
            db.commit()
        elif settings.sync_admin_password:
            # opt-in: keep the seeded admin's password in sync with INITIAL_ADMIN_PASSWORD
            if not security.verify_password(settings.initial_admin_password, admin.password_hash):
                admin.password_hash = security.hash_password(settings.initial_admin_password)
                admin.is_active = True
                db.commit()


app = create_app()