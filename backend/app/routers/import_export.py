import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..crypto import encrypt
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import AuditLog, PasswordEntry, User
from ..schemas import ImportConfirm, ImportPreview, ImportPreviewRow, ImportResult
from ..services import exporter, importer
from ..config import get_settings

router = APIRouter(prefix="/api", tags=["import-export"])

settings = get_settings()


@router.post("/import/preview", response_model=ImportPreview)
async def preview_import(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    try:
        parsed = importer.parse_import(data, file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    sample = [ImportPreviewRow(**row.__dict__) for row in parsed.rows[:5]]
    return ImportPreview(
        detected_format=parsed.detected_format,
        total_rows=len(parsed.rows),
        sample=sample,
        mapping=parsed.mapping,
    )


@router.post("/import/confirm", response_model=ImportResult)
async def confirm_import(
    file: UploadFile = File(...),
    body: ImportConfirm = ImportConfirm(),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = await file.read()
    try:
        parsed = importer.parse_import(data, file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if len(parsed.rows) > settings.max_import_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds limit of {settings.max_import_rows} rows",
        )

    mapping = {k: v for k, v in body.mapping.items() if v}
    if "password" not in parsed.mapping:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No password column mapped")
    for field in ("title", "url", "username", "password", "notes"):
        if field not in mapping:
            mapping[field] = parsed.mapping.get(field, "")

    imported = 0
    skipped = 0
    failed = 0
    existing = {(e.title.lower(), e.url.lower()) for e in db.query(PasswordEntry).all()}

    for row in parsed.rows:
        try:
            if body.skip_duplicates and (row.title.lower(), row.url.lower()) in existing:
                skipped += 1
                continue
            entry = PasswordEntry(
                title=row.title[:255],
                url=row.url[:1024],
                username_cipher=encrypt(row.username),
                password_cipher=encrypt(row.password),
                notes_cipher=encrypt(row.notes),
                category=row.category,
                owner_id=admin.id,
            )
            db.add(entry)
            db.flush()
            existing.add((row.title.lower(), row.url.lower()))
            imported += 1
        except Exception:
            failed += 1

    db.add(AuditLog(user_id=admin.id, action="import.run",
                    detail=f"imported={imported} skipped={skipped} failed={failed} format={parsed.detected_format}"))
    db.commit()
    return ImportResult(imported=imported, skipped_duplicates=skipped, failed=failed)


@router.get("/export")
def export_entries(
    format: str = "csv",
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    entries = db.query(PasswordEntry).order_by(PasswordEntry.title).all()
    if format == "xlsx":
        content = exporter.export_xlsx(entries)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "vault-export.xlsx"
    else:
        content = exporter.export_csv(entries)
        media = "text/csv; charset=utf-8"
        filename = "vault-export.csv"

    db.add(AuditLog(user_id=admin.id, action="export.run", detail=f"format={format} rows={len(entries)}"))
    db.commit()
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )