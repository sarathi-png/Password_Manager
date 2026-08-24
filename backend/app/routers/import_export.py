import io
import json
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..crypto import decrypt, encrypt
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import AuditLog, Category, District, Block, PasswordEntry, User
from ..schemas import ImportConfirm, ImportPreview, ImportPreviewRow, ImportResult
from ..services import exporter, importer
from ..services.smart_categorizer import group_by_registrable, host_group_key_for, propose_smart_groups, registrable_domain
from ..config import get_settings

router = APIRouter(prefix="/api", tags=["import-export"])

logger = logging.getLogger("vault.import")

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
    # host groups collapsed by registrable domain (lokos.in merges subdomains)
    host_groups = group_by_registrable(parsed.rows)
    # smart analysis (rule + optional AI) — permit step decides whether to apply
    smart_groups = propose_smart_groups(host_groups, use_ai=True)
    # convert to schemas
    from ..schemas import HostGroup as HostGroupSchema, SmartGroup as SmartGroupSchema
    hg = [HostGroupSchema(registrable_domain=g["registrable_domain"], exact_hosts=g["exact_hosts"], count=g["count"], sample_titles=g["sample_titles"]) for g in host_groups]
    sg = [SmartGroupSchema(registrable_domain=g["registrable_domain"], count=g["count"], proposed_category=g["proposed_category"], proposed_subcategory=g.get("proposed_subcategory"), confidence=g["confidence"], is_ai=g["is_ai"]) for g in smart_groups]
    return ImportPreview(
        detected_format=parsed.detected_format,
        total_rows=len(parsed.rows),
        sample=sample,
        mapping=parsed.mapping,
        host_groups=hg,
        smart_groups=sg,
    )


@router.post("/import/confirm", response_model=ImportResult)
async def confirm_import(
    file: UploadFile = File(...),
    mapping: str = Form(default="{}"),
    district_id: int | None = Form(default=None),
    block_id: int | None = Form(default=None),
    skip_duplicates: bool = Form(default=False),
    dedup_mode: str = Form(default="none"),
    permit_smart: bool = Form(default=False),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # Backward compat: mapping may be JSON string or already parsed; also support body JSON via query fallback
    try:
        parsed_mapping = json.loads(mapping) if isinstance(mapping, str) else {}
    except Exception:
        parsed_mapping = {}
    # Reconstruct ImportConfirm-like object for internal logic
    class _Body:
        pass
    body = _Body()
    body.mapping = parsed_mapping if parsed_mapping else {}
    body.skip_duplicates = skip_duplicates
    body.dedup_mode = dedup_mode
    body.district_id = district_id
    body.block_id = block_id
    body.permit_smart = permit_smart

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

    mapping_dict = {k: v for k, v in body.mapping.items() if v}
    # if no mapping provided, fall back to auto-detected
    if not mapping_dict:
        mapping_dict = dict(parsed.mapping)
    if "password" not in parsed.mapping and "password" not in mapping_dict:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No password column mapped")
    for field in ("title", "url", "username", "password", "notes"):
        if field not in mapping_dict:
            mapping_dict[field] = parsed.mapping.get(field, "")

    imported = 0
    skipped = 0
    failed = 0
    marked_duplicates = 0
    row_errors: list[str] = []

    # Build existing key set for duplicate detection / marking
    dedup_mode = getattr(body, "dedup_mode", "none") or "none"
    # validate district/block if provided
    target_district_id = getattr(body, "district_id", None)
    target_block_id = getattr(body, "block_id", None)
    if target_district_id is not None and db.get(District, target_district_id) is None:
        raise HTTPException(status_code=400, detail="District not found")
    if target_block_id is not None and db.get(Block, target_block_id) is None:
        raise HTTPException(status_code=400, detail="Block not found")

    def _key_for(row):
        t = row.title.strip().lower()
        u = row.url.strip().lower()
        un = row.username.strip().lower()
        pw = row.password  # password case-sensitive, but still normalize lower for grouping? keep case-sensitive
        if dedup_mode == "exact":
            return (t, u, un, pw)
        if dedup_mode == "title_url_username":
            return (t, u, un)
        if dedup_mode == "title_url":
            return (t, u)
        return None  # "none" → no dedup key, but still mark via title_url for is_duplicate flag

    # For is_duplicate flag we still want to mark duplicates on title+url (broad) even when dedup_mode=="none"
    # So build both a strict key set and a broad key set
    broad_existing = {(e.title.lower(), e.url.lower()) for e in db.query(PasswordEntry).all()}
    strict_existing: set = set()
    if dedup_mode != "none":
        # For strict modes we need to include username/password if required; we build from DB decrypted
        # This is O(N) decrypt - acceptable up to 50k; if too large we fallback to broad
        try:
            for e in db.query(PasswordEntry).all():
                t = e.title.strip().lower()
                u = e.url.strip().lower()
                if dedup_mode == "exact":
                    un = decrypt(e.username_cipher).strip().lower() if e.username_cipher else ""
                    pw = decrypt(e.password_cipher) if e.password_cipher else ""
                    strict_existing.add((t, u, un, pw))
                elif dedup_mode == "title_url_username":
                    un = decrypt(e.username_cipher).strip().lower() if e.username_cipher else ""
                    strict_existing.add((t, u, un))
                elif dedup_mode == "title_url":
                    strict_existing.add((t, u))
        except Exception:
            strict_existing = set(broad_existing)

    # smart grouping (registrable domain) for host fields + optional AI category
    host_groups = group_by_registrable(parsed.rows)
    smart_groups = propose_smart_groups(host_groups, use_ai=True) if getattr(body, "permit_smart", False) else []
    smart_map: dict[str, int | None] = {}
    if getattr(body, "permit_smart", False):
        # ensure Category rows exist for proposed names
        for g in smart_groups:
            name = g["proposed_category"]
            cat = db.query(Category).filter(Category.name == name).first()
            if not cat:
                cat = Category(name=name, slug=name.lower().replace(" ", "-"), is_system=False)
                db.add(cat)
                db.flush()
            smart_map[g["registrable_domain"]] = cat.id

    for idx, row in enumerate(parsed.rows, start=1):
        try:
            # Determine duplicate status for marking
            broad_key = (row.title.lower(), row.url.lower())
            is_dup_broad = broad_key in broad_existing
            # strict check if mode != none
            is_dup = is_dup_broad
            if dedup_mode != "none":
                k = _key_for(row)
                if k is not None:
                    is_dup = k in strict_existing

            # Skip only if explicitly asked
            if getattr(body, "skip_duplicates", False) and is_dup and dedup_mode != "none":
                skipped += 1
                continue

            # Mark as duplicate but still import
            is_duplicate_flag = is_dup
            # host grouping
            h, reg, _key = host_group_key_for(row.url)
            host_val = h
            exact_val = h
            reg_val = reg
            host_key = reg or h
            smart_cat_id = smart_map.get(reg) if getattr(body, "permit_smart", False) else None

            entry = PasswordEntry(
                title=row.title[:255],
                url=row.url[:1024],
                username_cipher=encrypt(row.username),
                password_cipher=encrypt(row.password),
                notes_cipher=encrypt(row.notes),
                category=row.category,
                owner_id=admin.id,
                district_id=target_district_id,
                block_id=target_block_id,
                is_duplicate=is_duplicate_flag,
                host=host_val[:255],
                exact_host=exact_val[:255],
                registrable_domain=reg_val[:255],
                host_group_key=host_key[:255],
                smart_category_id=smart_cat_id,
            )
            db.add(entry)
            db.flush()
            broad_existing.add(broad_key)
            if dedup_mode != "none":
                k = _key_for(row)
                if k is not None:
                    strict_existing.add(k)
            if is_duplicate_flag:
                marked_duplicates += 1
            imported += 1
        except Exception as exc:
            failed += 1
            # A failed flush poisons the session — roll back so later rows can proceed
            db.rollback()
            logger.exception("Import row %d failed (title=%r url=%r)", idx, row.title[:80], row.url[:120])
            if len(row_errors) < 5:
                row_errors.append(f"row {idx} ({row.title[:60] or 'untitled'}): {type(exc).__name__}: {exc}")

    first_error = row_errors[0] if row_errors else ""
    db.add(AuditLog(user_id=admin.id, action="import.run",
                    detail=f"imported={imported} skipped={skipped} marked_dup={marked_duplicates} failed={failed} format={parsed.detected_format}"
                           + (f" first_error={first_error[:300]}" if first_error else "")))
    db.commit()
    return ImportResult(imported=imported, skipped_duplicates=skipped, failed=failed,
                        marked_duplicates=marked_duplicates, errors=row_errors)


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