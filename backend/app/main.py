from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import security
from .config import get_settings
from .database import Base, SessionLocal, engine
from .models import AuditLog, User
from .routers import audit, auth, categories, districts, entries, import_export, profiles, users
from sqlalchemy import inspect, text

logger = logging.getLogger("vault.migrations")
logging.basicConfig(level=logging.INFO)

settings = get_settings()
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _ensure_migrations():
    """Lightweight SQLite/Postgres migration for added columns (for Render free deploy without alembic).

    Each ALTER runs in its own transaction so one failure cannot skip the remaining columns.
    """
    try:
        insp = inspect(engine)

        def _add_column(table: str, col: str, ddl: str) -> None:
            # fresh inspector each check — Inspector caches column info
            cols = {c["name"] for c in inspect(engine).get_columns(table)}
            if col in cols:
                return
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
                logger.info("Migration: added %s.%s", table, col)
            except Exception:
                logger.exception("Migration FAILED: %s.%s (%s)", table, col, ddl)

        # users scope columns
        if "users" in insp.get_table_names():
            _add_column("users", "district_id", "INTEGER")
            _add_column("users", "block_id", "INTEGER")

        # password_entries smart-grouping + scope columns
        if "password_entries" in insp.get_table_names():
            _add_column("password_entries", "district_id", "INTEGER")
            _add_column("password_entries", "block_id", "INTEGER")
            # Postgres needs FALSE, SQLite accepts 0; use FALSE for compat, SQLite will coerce
            _add_column("password_entries", "is_duplicate", "BOOLEAN NOT NULL DEFAULT FALSE")
            for col, typ in [
                ("host", "VARCHAR(255)"),
                ("exact_host", "VARCHAR(255)"),
                ("registrable_domain", "VARCHAR(255)"),
                ("host_group_key", "VARCHAR(255)"),
                ("smart_category_id", "INTEGER"),
                ("smart_subcategory_id", "INTEGER"),
            ]:
                _add_column("password_entries", col, typ)

        # categories sort_order column
        if "categories" in insp.get_table_names():
            _add_column("categories", "sort_order", "INTEGER NOT NULL DEFAULT 999")
            # update existing system categories with correct sort_order
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        UPDATE categories SET sort_order = CASE name
                            WHEN 'Email' THEN 1 WHEN 'Banking' THEN 2 WHEN 'Social' THEN 3
                            WHEN 'Shopping' THEN 4 WHEN 'Work' THEN 5 WHEN 'Entertainment' THEN 6
                            WHEN 'Other' THEN 7 ELSE sort_order END
                        WHERE is_system = true
                    """))
                logger.info("Updated sort_order for system categories")
            except Exception:
                logger.exception("Failed to update sort_order for system categories")

        # password_entries search_vector column + GIN index (PostgreSQL only)
        if "password_entries" in insp.get_table_names():
            _add_column("password_entries", "search_vector", "TSVECTOR")
            # Create GIN index for full-text search (PostgreSQL only)
            try:
                with engine.begin() as conn:
                    # Check if index exists first
                    result = conn.execute(text("""
                        SELECT 1 FROM pg_indexes WHERE indexname = 'ix_password_entries_search_vector'
                    """))
                    if not result.fetchone():
                        conn.execute(text("""
                            CREATE INDEX ix_password_entries_search_vector 
                            ON password_entries USING GIN (search_vector)
                        """))
                        logger.info("Created GIN index on password_entries.search_vector")
            except Exception:
                # SQLite doesn't support GIN index, ignore
                logger.debug("GIN index creation skipped (likely SQLite)")

        # users search_include_password column
        if "users" in insp.get_table_names():
            _add_column("users", "search_include_password", "BOOLEAN NOT NULL DEFAULT FALSE")

        # password_entries profile_id column
        if "password_entries" in insp.get_table_names():
            _add_column("password_entries", "profile_id", "INTEGER")

        # profiles table
        if "profiles" not in insp.get_table_names():
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE profiles (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(128) NOT NULL,
                            avatar_url VARCHAR(512) NOT NULL DEFAULT '',
                            created_by_id INTEGER,
                            created_at TIMESTAMP NOT NULL DEFAULT NOW()
                        )
                    """))
                logger.info("Created profiles table")
            except Exception:
                logger.debug("profiles table creation skipped (likely exists)")

        # user_profiles table
        if "user_profiles" not in insp.get_table_names():
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE user_profiles (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER NOT NULL,
                            profile_id INTEGER NOT NULL,
                            pin_hash VARCHAR(128),
                            created_at TIMESTAMP NOT NULL DEFAULT NOW()
                        )
                    """))
                    conn.execute(text("CREATE INDEX ix_user_profiles_user_id ON user_profiles (user_id)"))
                    conn.execute(text("CREATE INDEX ix_user_profiles_profile_id ON user_profiles (profile_id)"))
                logger.info("Created user_profiles table")
            except Exception:
                logger.debug("user_profiles table creation skipped (likely exists)")

        try:
            with engine.begin() as conn:
                conn.execute(text("UPDATE password_entries SET is_duplicate = FALSE WHERE is_duplicate IS NULL"))
                conn.execute(text("UPDATE password_entries SET host = '' WHERE host IS NULL"))
                conn.execute(text("UPDATE password_entries SET host_group_key = COALESCE(registrable_domain, host, '') WHERE host_group_key IS NULL OR host_group_key = ''"))
        except Exception:
            logger.exception("Backfill after column migration failed")

        # verify: scream if anything required is still missing
        if "password_entries" in insp.get_table_names():
            have = {c["name"] for c in inspect(engine).get_columns("password_entries")}
            required = {"district_id", "block_id", "is_duplicate", "host", "exact_host",
                        "registrable_domain", "host_group_key", "smart_category_id", "smart_subcategory_id",
                        "search_vector", "profile_id"}
            missing = required - have
            if missing:
                logger.error("Schema verification FAILED — password_entries still missing columns: %s", sorted(missing))
            else:
                logger.info("Schema migration check completed — password_entries has all required columns")
    except Exception:
        logger.exception("Schema migration crashed unexpectedly")

    # seed system categories
    try:
        from .models import Category
        with SessionLocal() as db:
            if db.query(Category).count() == 0:
                # System categories in the desired display order (matching frontend CATEGORIES)
                # sort_order: Email=1, Banking=2, Social=3, Shopping=4, Work=5, Entertainment=6, Other=7
                system_cats = [
                    ("Email", 1), ("Banking", 2), ("Social", 3), ("Shopping", 4),
                    ("Work", 5), ("Entertainment", 6), ("Other", 7),
                ]
                for name, sort_order in system_cats:
                    db.add(Category(name=name, slug=name.lower(), parent_id=None, is_system=True, sort_order=sort_order))
                db.commit()
    except Exception:
        logger.exception("Category seeding failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_migrations()
    _warm_vault_key()
    seed_admin()
    yield


def _warm_vault_key() -> None:
    """Fail fast (loudly) if VAULT_MASTER_KEY is misconfigured, instead of failing on first encrypt."""
    from .crypto import _get_key

    try:
        _get_key()
        logger.info("Vault master key loaded OK")
    except Exception as exc:
        logger.error("VAULT MASTER KEY MISCONFIGURED — encrypt/decrypt will fail until fixed: %s", exc)


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
    app.include_router(profiles.router)
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