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
from .routers import audit, auth, entries, import_export, users

settings = get_settings()
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
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
        if db.query(User).filter(User.role == "admin").count() == 0:
            admin = User(
                username=settings.initial_admin_username,
                password_hash=security.hash_password(settings.initial_admin_password),
                role="admin",
            )
            db.add(admin)
            db.commit()


app = create_app()